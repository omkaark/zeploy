import os
import json
import subprocess
import threading
import logging
import time
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

app = Flask(__name__)

FUSE_MOUNT_DIR = "/mnt/fuse"
FILE_SERVER_URL = os.environ.get('FILE_SERVER_URL', 'http://localhost:8192')

def run_container(image_name):
    logger.info(f"Attempting to run container for image: {image_name}")
    config_path = os.path.join(FUSE_MOUNT_DIR, "config.json")
    logger.info(f"Config path: {config_path}")

    # Wait for config file to become available (with timeout)
    timeout = 30
    start_time = time.time()
    logger.info(f"Waiting for config file to become available (timeout: {timeout}s)")
    while not os.path.exists(config_path):
        if time.time() - start_time > timeout:
            logger.error(f"Config file not found after waiting: {config_path}")
            return jsonify({"error": "Config file not found after waiting"}), 404
        time.sleep(0.5)

    logger.info(f"Config file found: {config_path}")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.debug(f"Loaded config: {json.dumps(config, indent=2)}")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from config file: {e}")
        return jsonify({"error": f"Invalid JSON in config file: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Error reading config file: {e}")
        return jsonify({"error": f"Error reading config file: {str(e)}"}), 500

    try:
        logger.info(f"Running crun for image: {image_name}")
        result = subprocess.run(["crun", "run", "-b", f"/mnt/fuse/", image_name], 
                                capture_output=True, text=True, check=True, timeout=60)
        logger.info("crun command completed successfully")
        logger.debug(f"crun stdout: {result.stdout}")
        logger.debug(f"crun stderr: {result.stderr}")
        return jsonify({"output": result.stdout, "error": result.stderr})
    except subprocess.TimeoutExpired as e:
        logger.error(f"Timeout running crun for {image_name}")
        return jsonify({"error": "Timeout running container", "output": e.stdout, "error_output": e.stderr}), 504
    except subprocess.CalledProcessError as e:
        logger.exception(f"Error running crun for {image_name}")
        logger.error(f"crun stdout: {e.stdout}")
        logger.error(f"crun stderr: {e.stderr}")
        return jsonify({"error": str(e), "output": e.stdout, "error_output": e.stderr}), 500
    except Exception as e:
        logger.exception(f"Unexpected error running crun for {image_name}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/run', methods=['GET'])
def run_container_api():
    logger.info("Received request to /run endpoint")
    data = request.args
    if 'image_name' not in data:
        logger.warning("Missing image_name in request")
        return jsonify({"error": "Missing image_name in request"}), 400

    logger.info(f"Running container for image: {data['image_name']}")
    return run_container(data['image_name'])

@app.route('/health', methods=['GET'])
def health_check():
    logger.info("Health check requested")
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    logger.info('API server starting...')
    app.run(host='0.0.0.0', port=8082)