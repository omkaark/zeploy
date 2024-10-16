from http.server import BaseHTTPRequestHandler
import socketserver
import os
import urllib.parse
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileServerHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.root = "images"
        super().__init__(*args, **kwargs)

    def _parse_path(self, path):
        parts = path.lstrip('/').split('/', 1)
        image_name = parts[0] if parts else ''
        file_path = parts[1] if len(parts) > 1 else ''
        return image_name, file_path

    def _full_path(self, partial):
        image_name, file_path = self._parse_path(partial)
        if not image_name:
            return self.root
        return os.path.join(self.root, image_name, file_path)
    
    def _send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)
        logger.debug(f"Received GET request: {path} with query {query}")

        try:
            if path == "/access":
                self._handle_access(query)
            elif path == "/getattr":
                self._handle_getattr(query)
            elif path == "/readdir":
                self._handle_readdir(query)
            elif path == "/read":
                self._handle_read(query)
            elif path == "/readlink":
                self._handle_readlink(query)
            elif path == "/open":
                self._handle_open(query)
            elif path == "/release":
                self._handle_release(query)
            elif path == "/statfs":
                self._handle_statfs(query)
            else:
                self.send_error(404, "Endpoint not found")
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            self.send_error(500, "Internal server error")

    def _handle_access(self, query):
        path = self._full_path(query.get('path', [''])[0])
        mode = int(query.get('mode', [0])[0])
        if not os.access(path, mode):
            self.send_error(403, "Access denied")
        else:
            self._send_json_response({"success": True})

    def _handle_getattr(self, query):
        path = self._full_path(query.get('path', [''])[0])
        try:
            st = os.lstat(path)
            attrs = dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))
            self._send_json_response(attrs)
        except OSError:
            self.send_error(404, "File not found")

    def _handle_readdir(self, query):
        path = self._full_path(query.get('path', [''])[0])
        if os.path.isdir(path):
            dirents = ['.', '..'] + os.listdir(path)
            self._send_json_response(dirents)
        else:
            self.send_error(404, "Directory not found")

    def _handle_readlink(self, query):
        path = self._full_path(query.get('path', [''])[0])
        try:
            target = os.readlink(path)
            self._send_json_response({"target": target})
        except OSError:
            self.send_error(404, "Symlink not found")

    def _handle_statfs(self, query):
        path = self._full_path(query.get('path', [''])[0])
        try:
            stv = os.statvfs(path)
            result = dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
                'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
                'f_frsize', 'f_namemax'))
            self._send_json_response(result)
        except OSError:
            self.send_error(404, "Path not found")

    def _handle_open(self, query):
        path = self._full_path(query.get('path', [''])[0])
        flags = int(query.get('flags', [os.O_RDONLY])[0])
        try:
            fh = os.open(path, flags)
            self._send_json_response({"fh": fh})
        except OSError:
            self.send_error(404, "File not found")

    def _handle_read(self, query):
        path = self._full_path(query.get('path', [''])[0])
        size = int(query.get('size', [0])[0])
        offset = int(query.get('offset', [0])[0])
        fh = int(query.get('fh', [0])[0])
        try:
            with open(path, 'rb') as f:
                f.seek(offset)
                data = f.read(size)
            self._send_json_response({"data": data.hex()})
        except OSError:
            self.send_error(404, "File not found")

    def _handle_release(self, query):
        fh = int(query.get('fh', [0])[0])
        try:
            os.close(fh)
            self._send_json_response({"success": True})
        except OSError:
            self.send_error(500, "Error closing file handle")

if __name__ == "__main__":
    print("Serving files from file_server/images on port 8192")
    with socketserver.TCPServer(("0.0.0.0", 8192), FileServerHandler) as httpd:
        print("Serving on 0.0.0.0:8192")
        httpd.serve_forever()