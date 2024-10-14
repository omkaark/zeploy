import errno
import os
from fuse import FUSE, FuseOSError, Operations
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReadOnlyLocalFS(Operations):
    def __init__(self, image_name):
        self.image_name = image_name
        self.base_url = os.environ.get('FILE_SERVER_URL', 'http://localhost:8192')

    def _make_request(self, endpoint, params={}):
        url = f"{self.base_url}/{endpoint}"
        params['image_name'] = self.image_name
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error making request to {url}: {str(e)}")
            raise FuseOSError(errno.EIO)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {url}: {str(e)}")
            raise FuseOSError(errno.EIO)

    def access(self, path, mode):
        try:
            self._make_request("access", {"path": path, "mode": mode})
        except FuseOSError as e:
            if e.errno == errno.EIO:
                raise FuseOSError(errno.EACCES)
            raise

    def getattr(self, path, fh=None):
        return self._make_request("getattr", {"path": path})

    def readdir(self, path, fh):
        dirents = self._make_request("readdir", {"path": path})
        for r in dirents:
            yield r

    def readlink(self, path):
        response = self._make_request("readlink", {"path": path})
        return response['target']

    def statfs(self, path):
        return self._make_request("statfs", {"path": path})

    def open(self, path, flags):
        response = self._make_request("open", {"path": path, "flags": flags})
        return response['fh']

    def read(self, path, size, offset, fh):
        response = self._make_request("read", {"path": path, "size": size, "offset": offset, "fh": fh})
        return bytes.fromhex(response['data'])

    def release(self, path, fh):
        self._make_request("release", {"path": path, "fh": fh})

    # Read-only operations (raise EROFS)
    def mknod(self, path, mode, dev):
        raise FuseOSError(errno.EROFS)

    def rmdir(self, path):
        raise FuseOSError(errno.EROFS)

    def mkdir(self, path, mode):
        raise FuseOSError(errno.EROFS)

    def chmod(self, path, mode):
        raise FuseOSError(errno.EROFS)

    def chown(self, path, uid, gid):
        raise FuseOSError(errno.EROFS)

    def create(self, path, mode, fi=None):
        raise FuseOSError(errno.EROFS)

    def unlink(self, path):
        raise FuseOSError(errno.EROFS)

    def symlink(self, name, target):
        raise FuseOSError(errno.EROFS)

    def rename(self, old, new):
        raise FuseOSError(errno.EROFS)

    def link(self, target, name):
        raise FuseOSError(errno.EROFS)

    def utimens(self, path, times=None):
        raise FuseOSError(errno.EROFS)

    def write(self, path, buf, offset, fh):
        raise FuseOSError(errno.EROFS)

    def truncate(self, path, length, fh=None):
        raise FuseOSError(errno.EROFS)

    def fsync(self, path, fdatasync, fh):
        raise FuseOSError(errno.EROFS)

    def flush(self, path, fh):
        pass

def mount_fuse(mount_point, image_name, foreground=True):
    FUSE(ReadOnlyLocalFS(image_name), mount_point, nothreads=True, foreground=foreground, allow_other=True, ro=True)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print('usage: %s <mountpoint> <image_name>' % sys.argv[0])
        exit(1)
    mount_fuse(sys.argv[1], sys.argv[2])