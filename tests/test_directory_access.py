from .tools import ipfs_dir
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
