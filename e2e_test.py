import os
import stat
import unittest
import subprocess

class TestFUSEFileSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mount_point = "/mnt/fuse"
        cls.server_url = "http://localhost:8192"
        
        if not os.path.ismount(cls.mount_point):
            raise Exception(f"FUSE filesystem not mounted at {cls.mount_point}")

    def test_access(self):
        file_path = f"{self.mount_point}/bin/sh"
        self.assertTrue(os.access(file_path, os.R_OK), f"Cannot access {file_path} with read permissions")
        non_existent = f"{self.mount_point}/non_existent_file"
        self.assertFalse(os.access(non_existent, os.F_OK), f"Non-existent file {non_existent} appears to exist")

    def test_getattr(self):
        file_path = f"{self.mount_point}/bin/sh"
        st = os.stat(file_path)
        self.assertTrue(stat.S_ISREG(st.st_mode), f"{file_path} is not a regular file")
        dir_path = f"{self.mount_point}/app"
        st = os.stat(dir_path)
        self.assertTrue(stat.S_ISDIR(st.st_mode), f"{dir_path} is not a directory")

    def test_readdir(self):
        root_contents = os.listdir(self.mount_point)
        self.assertIn("bin", root_contents, f"'bin' directory not found in {self.mount_point}")
        self.assertIn("app", root_contents, f"'app' directory not found in {self.mount_point}")
        app_contents = os.listdir(f"{self.mount_point}/app")
        self.assertIn("hello.py", app_contents, f"'hello.py' not found in {self.mount_point}/app")

    def test_readlink(self):
        symlink_path = f"{self.mount_point}/bin/sh"
        if os.path.islink(symlink_path):
            link_target = os.readlink(symlink_path)
            self.assertIsNotNone(link_target, f"Symlink {symlink_path} has no target")

    def test_statfs(self):
        stats = os.statvfs(self.mount_point)
        self.assertIsNotNone(stats, f"Failed to get filesystem stats for {self.mount_point}")
        self.assertGreater(stats.f_bsize, 0, f"Invalid block size ({stats.f_bsize}) for {self.mount_point}")

    def test_open_read_close(self):
        file_path = f"{self.mount_point}/app/hello.py"
        with open(file_path, 'r') as f:
            content = f.read()
        self.assertIsNotNone(content, f"Failed to read content from {file_path}")
        self.assertGreater(len(content), 0, f"File {file_path} is empty")

    def test_large_file_read(self):
        file_path = f"{self.mount_point}/bin/sh"
        chunk_size = 4096
        total_size = 0
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                total_size += len(chunk)
        self.assertGreater(total_size, chunk_size, 
                           f"File {file_path} is not larger than the chunk size ({chunk_size} bytes)")

    def test_execute_binary(self):
        sh_path = f"{self.mount_point}/bin/sh"
        self.assertTrue(os.path.exists(sh_path), f"{sh_path} does not exist")
        st = os.stat(sh_path)
        self.assertTrue(st.st_mode & stat.S_IXUSR, f"{sh_path} is not executable")
        
        try:
            result = subprocess.run([sh_path, "-c", "echo 'Hello from mounted sh'"], 
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, f"Failed to execute {sh_path}")
            self.assertIn("Hello from mounted sh", result.stdout, 
                          f"Expected output not found when executing {sh_path}")
        except subprocess.TimeoutExpired:
            self.fail(f"Execution of {sh_path} timed out")

    def test_read_empty_file(self):
        empty_file_path = f"{self.mount_point}/empty_file.txt"
        with self.assertRaises(OSError, msg=f"Writing to read-only filesystem {empty_file_path} did not raise OSError"):
            with open(empty_file_path, 'w'):
                pass
        # If the file exists, test reading it
        if os.path.exists(empty_file_path):
            with open(empty_file_path, 'r') as f:
                content = f.read()
            self.assertEqual(content, "", f"File {empty_file_path} is not empty")

    def test_read_directory_as_file(self):
        dir_path = f"{self.mount_point}/app"
        with self.assertRaises(IsADirectoryError, msg=f"Reading directory {dir_path} as file did not raise IsADirectoryError"):
            with open(dir_path, 'r'):
                pass

    def test_file_stat(self):
        file_path = f"{self.mount_point}/bin/sh"
        st = os.stat(file_path)
        self.assertGreater(st.st_size, 0, f"File {file_path} has zero size")
        self.assertGreater(st.st_mtime, 0, f"File {file_path} has invalid modification time")
        self.assertGreater(st.st_atime, 0, f"File {file_path} has invalid access time")
        self.assertGreater(st.st_ctime, 0, f"File {file_path} has invalid creation time")

    def test_directory_traversal(self):
        for root, dirs, files in os.walk(self.mount_point):
            for d in dirs:
                dir_path = os.path.join(root, d)
                self.assertTrue(os.path.isdir(dir_path), f"{dir_path} is not a directory")
            for f in files:
                file_path = os.path.join(root, f)
                self.assertTrue(os.path.exists(file_path), f"{file_path} does not exist")
                # Check if it's a regular file, symlink, or other valid file type
                self.assertTrue(os.path.isfile(file_path) or os.path.islink(file_path) or stat.S_ISFIFO(os.stat(file_path).st_mode), 
                                f"{file_path} is not a valid file type")
                    
    def getattr(self, path, fh=None):
        full_path = self._full_path(path)
        st = os.lstat(full_path)
        attrs = dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                    'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))
        
        # Preserve execute permissions if they exist in the original file
        if st.st_mode & 0o111:  # Check if any execute bit is set
            attrs['st_mode'] |= 0o111  # Set execute bits for user, group, and others
        
        return attrs
    
    def test_file_permissions(self):
        file_path = f"{self.mount_point}/bin/sh"
        st = os.stat(file_path)
        self.assertTrue(st.st_mode & stat.S_IRUSR, f"{file_path} is not readable by user")
        self.assertTrue(st.st_mode & stat.S_IXUSR, f"{file_path} is not executable by user")

if __name__ == '__main__':
    unittest.main(verbosity=2)