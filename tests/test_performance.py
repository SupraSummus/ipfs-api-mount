from unittest import TestCase
import os

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
                object_data_cache_size=4,
                max_read=chunk_size,  # prevent FUSE from doing large reads to exagerate cache effects
                multithreaded=False,  # do everything in order to be more deterministic
            ) as mountpoint:

                with open(os.path.join(mountpoint, 'file'), 'rb') as f:
                    f.read()

            self.assertGreaterEqual(measuring_client.request_count, chunk_count)
            self.assertLess(measuring_client.request_count, 1.2 * chunk_count)
