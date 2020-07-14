from unittest import TestCase
import os
import subprocess

from ipfs_api_mount import InvalidIPFSPathException
from ipfs_api_mount.ipfs_mounted import ipfs_mounted

from tools import ipfs_client, ipfs_dir, ipfs_file


class DirectoryTestCase(TestCase):
    def test_empty_dir(self):
        root = ipfs_dir({})
        with ipfs_mounted(root, ipfs_client) as mountpoint:
            self.assertEqual(
                os.listdir(mountpoint),
                [],
            )

    def test_nonempty_dir(self):
        root = ipfs_dir({
            'aaa': ipfs_dir({}),
            'bbb': ipfs_dir({}),
        })
        with ipfs_mounted(root, ipfs_client) as mountpoint:
            self.assertEqual(
                os.listdir(mountpoint),
                ['aaa', 'bbb'],
            )

    def test_file_times(self):
        """creation/modification/access times for a file are all 0"""
        root = ipfs_dir({
            'bbb': ipfs_file(b'blabla'),
        })
        with ipfs_mounted(root, ipfs_client) as mountpoint:
            s = os.stat(os.path.join(mountpoint, 'bbb'))
            self.assertEqual(s.st_ctime, 0)
            self.assertEqual(s.st_mtime, 0)
            self.assertEqual(s.st_atime, 0)

    def test_permission(self):
        root = ipfs_dir({})
        with ipfs_mounted(root, ipfs_client) as mountpoint:
            s = os.stat(mountpoint)
            self.assertEqual(
                s.st_mode,
                0o40555,
            )

    def test_permission_nested(self):
        root = ipfs_dir({
            'dir': ipfs_dir({}),
        })
        with ipfs_mounted(root, ipfs_client) as mountpoint:
            s = os.stat(os.path.join(mountpoint, 'dir'))
            self.assertEqual(
                s.st_mode,
                0o40555,
            )

    def test_cid_version_1(self):
        # constant cid because i'm lazy
        root = "bafybeiczsscdsbs7ffqz55asqdf3smv6klcw3gofszvwlyarci47bgf354"
        with ipfs_mounted(root, ipfs_client) as mountpoint:
            self.assertEqual(
                os.listdir(mountpoint),
                [],
            )


class FileTestCase(TestCase):
    def test_small_file_read(self):
        content = b'I forgot newline at the end. Ups.'
        root = ipfs_dir({'file': ipfs_file(content)})
        with ipfs_mounted(root, ipfs_client) as mountpoint:
            with open(os.path.join(mountpoint, 'file'), 'rb') as f:
                self.assertEqual(
                    f.read(),
                    content,
                )

    def test_10MiB_file_read(self):
        content = os.urandom(10 * 1024 * 1024)
        root = ipfs_dir({'file': ipfs_file(content)})
        with ipfs_mounted(root, ipfs_client) as mountpoint:
            with open(os.path.join(mountpoint, 'file'), 'rb') as f:
                self.assertEqual(
                    f.read(),
                    content,
                )

    def test_raw_leaves_small_file_read(self):
        content = b'precious'
        root = ipfs_dir({'file': ipfs_file(content, raw_leaves=True)})
        with ipfs_mounted(root, ipfs_client) as mountpoint:
            with open(os.path.join(mountpoint, 'file'), 'rb') as f:
                self.assertEqual(
                    f.read(),
                    content,
                )

    def test_raw_leaves_10MiB_file(self):
        content = os.urandom(10 * 1024 * 1024)
        root = ipfs_dir({'file': ipfs_file(content, raw_leaves=True)})
        with ipfs_mounted(root, ipfs_client) as mountpoint:
            with open(os.path.join(mountpoint, 'file'), 'rb') as f:
                self.assertEqual(
                    f.read(),
                    content,
                )

    def test_cid_version_1_small_file(self):
        content = "this is next gen file"
        root = subprocess.run(
            f'echo "{content}" | ipfs add --cid-version 1 --wrap-with-directory --quieter --stdin-name file',
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout.decode('ascii').strip()
        with ipfs_mounted(root, ipfs_client) as mountpoint:
            with open(os.path.join(mountpoint, 'file'), 'rb') as f:
                self.assertEqual(
                    f.read().decode('ascii'),
                    content + '\n',
                )


class ErrorsTestCase(TestCase):
    def test_invalid_root_hash(self):
        """ we should refuse to mount invalid hash """
        with self.assertRaises(InvalidIPFSPathException):
            with ipfs_mounted('straight/to/nonsense', ipfs_client):
                pass

    def test_file_root_hash(self):
        """ we should refuse to mount something that is a file (dir is needed) """
        root = ipfs_file(b'definetly not a dir')
        with self.assertRaises(InvalidIPFSPathException):
            with ipfs_mounted(root, ipfs_client):
                pass

    def test_complex_root_hash(self):
        root = ipfs_dir({
            'nested_dir': ipfs_dir({
                'empty_dir': ipfs_dir({}),
            }),
        })
        with ipfs_mounted(root + '/nested_dir', ipfs_client) as mountpoint:
            self.assertEqual(
                os.listdir(mountpoint),
                ['empty_dir'],
            )

    def test_nonexistent_file(self):
        """ there is no way we can open nonexistent file """
        root = ipfs_dir({})
        with ipfs_mounted(root, ipfs_client) as mountpoint:
            with self.assertRaises(FileNotFoundError):
                open(os.path.join(mountpoint, 'a_file'), 'rb')
