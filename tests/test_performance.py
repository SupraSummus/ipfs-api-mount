from unittest import TestCase
import os
import subprocess

from ipfs_api_mount.ipfs_mounted import ipfs_mounted

from .tools import ipfs_dir, ipfs_file, MeasuringClient


class FilePerformanceTestCase(TestCase):
    def test_file_read(self):
        """ Reading a file causes at most as many requests as there are blocks in the file. """
        chunk_count = 100
        chunk_size = 4096
        content = os.urandom(chunk_count * chunk_size)
        root = ipfs_dir({'file': ipfs_file(content, chunker=f'size-{chunk_size}')})

        with MeasuringClient() as measuring_client:

            with ipfs_mounted(
                root, measuring_client,
                link_cache_size=4,
                max_read=chunk_size,  # prevent FUSE from doing large reads to exagerate cache effects
                multithreaded=False,  # do everything in order to be more deterministic
            ) as mountpoint:

                with open(os.path.join(mountpoint, 'file'), 'rb') as f:
                    f.read()

            self.assertGreaterEqual(measuring_client.request_count, chunk_count)
            self.assertLess(measuring_client.request_count, 1.2 * chunk_count)


class DirectoryPerformanceTestCase(TestCase):
    def test_file_attribute_cache(self):
        """ Getting file attributes second time causes no new requests """
        n = 100
        root = ipfs_dir({
            str(i): ipfs_file(b'conent' + str(i).encode('ascii'))
            for i in range(n)
        })

        ls_kwargs = dict(
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        # cache gets overflowed
        with MeasuringClient() as measuring_client:
            with ipfs_mounted(
                root, measuring_client,
                attr_cache_size=int(n * 0.9),
                attr_timeout=0,  # disable FUSE-level caching
            ) as mountpoint:
                subprocess.run(['ls', '-l', mountpoint], **ls_kwargs)
                measuring_client.clear_request_count()
                subprocess.run(['ls', '-l', mountpoint], **ls_kwargs)
                self.assertGreaterEqual(measuring_client.request_count, n)

        # now cache size is sufficient
        with MeasuringClient() as measuring_client:
            with ipfs_mounted(
                root, measuring_client,
                attr_cache_size=int(n * 1.1),
                attr_timeout=0,  # disable FUSE-level caching
            ) as mountpoint:
                subprocess.run(['ls', '-l', mountpoint], **ls_kwargs)
                measuring_client.clear_request_count()
                subprocess.run(['ls', '-l', mountpoint], **ls_kwargs)
                self.assertLess(measuring_client.request_count, n * 0.1)
