from .tools import ipfs_dir, ipfs_file
from ipfs_api_mount.ipfs_mounted import ipfs_mounted
from unittest import TestCase
import os


class DirectoryTestCase(TestCase):
    def test_empty_dir(self):
        root = ipfs_dir({})
        with ipfs_mounted(root) as mountpoint:
            self.assertEqual(
                os.listdir(mountpoint),
                [],
            )

    def test_nonempty_dir(self):
        root = ipfs_dir({
            'aaa': ipfs_dir({}),
            'bbb': ipfs_dir({}),
        })
        with ipfs_mounted(root) as mountpoint:
            self.assertEqual(
                os.listdir(mountpoint),
                ['aaa', 'bbb'],
            )


class FileTestCase(TestCase):
    def test_small_file_read(self):
        content = b'I forgot newline at the end. Ups.'
        root = ipfs_dir({'file': ipfs_file(content)})
        with ipfs_mounted(root) as mountpoint:
            with open(os.path.join(mountpoint, 'file'), 'rb') as f:
                self.assertEqual(
                    f.read(),
                    content,
                )

    def test_10MiB_file_read(self):
        content = os.urandom(10 * 1024 * 1024)
        root = ipfs_dir({'file': ipfs_file(content)})
        with ipfs_mounted(root) as mountpoint:
            with open(os.path.join(mountpoint, 'file'), 'rb') as f:
                self.assertEqual(
                    f.read(),
                    content,
                )
