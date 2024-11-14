import os
import json
import subprocess
import logging
import tempfile
import shutil
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

FUSE_MOUNT_DIR = "/mnt/fuse"

def generate_config(image_name, job_args):
    temp_bundle_dir = tempfile.mkdtemp(prefix='bundle_')
    fuse_image_dir = os.path.join(FUSE_MOUNT_DIR, image_name)
    lower_config_path = os.path.join(fuse_image_dir, "config.json")
    temp_config_path = os.path.join(temp_bundle_dir, "config.json")
    rootfs_source = fuse_image_dir  # Root filesystem is directly here
    rootfs_symlink = os.path.join(temp_bundle_dir, "rootfs")  # Symlink inside temp_bundle_dir

    # Read the original config.json
    with open(lower_config_path, 'r') as f:
        config = json.load(f)

    # Inject JOB_ARGS into the environment variables
    env = config['process'].get('env', [])
    env = [e for e in env if not e.startswith('JOB_ARGS=')]
    env.append(f"JOB_ARGS={job_args}")
    config['process']['env'] = env

    # Set root path to 'rootfs' (relative to bundle dir)
    config['root']['path'] = "rootfs"

    # Remove the network namespace to share the host's network
    namespaces = config['linux'].get('namespaces', [])
    config['linux']['namespaces'] = [ns for ns in namespaces if ns.get('type') != 'network']

    # Write the modified config.json to the temporary bundle
    with open(temp_config_path, 'w') as f:
        json.dump(config, f, indent=2)

    # Create a symlink to the actual rootfs
    os.symlink(rootfs_source, rootfs_symlink)

    return temp_bundle_dir

def run_container(image_name, job_args):
    temp_bundle_dir = None
    try:
        temp_bundle_dir = generate_config(image_name, job_args)

        logger.info(f"Running container for image: {image_name}")
        result = subprocess.run(
            ["crun", "run", "-b", temp_bundle_dir, image_name],
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )

        logger.info("Container run completed successfully")
        return jsonify({"output": result.stdout, "error": result.stderr})

    except subprocess.TimeoutExpired as e:
        logger.error(f"Timeout running container for {image_name}")
        return jsonify({
            "error": "Timeout running container",
            "output": e.stdout,
            "error_output": e.stderr
        }), 504

    except subprocess.CalledProcessError as e:
        logger.error(f"Error running container for {image_name}: {e}")
        return jsonify({
            "error": str(e),
            "output": e.stdout,
            "error_output": e.stderr
        }), 500

    except Exception as e:
        logger.exception(f"Unexpected error running container for {image_name}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

    finally:
        if temp_bundle_dir and os.path.exists(temp_bundle_dir):
            shutil.rmtree(temp_bundle_dir)

@app.route('/run', methods=['GET'])
def run_container_api():
    logger.info("Received request to /run endpoint")
    image_name = request.args.get('image_name')
    job_args = request.args.get('job_args')

    if not image_name:
        logger.warning("Missing image_name in request")
        return jsonify({"error": "Missing image_name in request"}), 400

    if not job_args:
        logger.warning("Missing job_args in request")
        return jsonify({"error": "Missing job_args in request"}), 400

    logger.info(f"Running container for image: {image_name} with job_args: {job_args}")
    return run_container(image_name, job_args)

@app.route('/health', methods=['GET'])
def health_check():
    logger.info("Health check requested")
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    logger.info('API server starting...')
    app.run(host='0.0.0.0', port=8082)
