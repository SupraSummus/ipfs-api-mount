import os
import subprocess

import pytest
from tools import ipfs_client, ipfs_dir, ipfs_file, request_count_measurement


@pytest.mark.skip(reason='max_read seems broken - https://github.com/libfuse/pyfuse3/issues/49')
def test_file_read(ipfs_mounted):
    """ Reading a file causes at most as many requests as there are blocks in the file. """
    chunk_count = 100
    chunk_size = 4096
    content = os.urandom(chunk_count * chunk_size)
    root = ipfs_dir({'file': ipfs_file(content, chunker=f'size-{chunk_size}')})

    with ipfs_mounted(
        root, ipfs_client,
        link_cache_size=4,
        fuse_kwargs=dict(
            max_read=chunk_size,  # prevent FUSE from doing large reads to exagerate cache effects
        ),
    ) as mountpoint:
        with request_count_measurement(ipfs_client) as mocked_request:

            with open(os.path.join(mountpoint, 'file'), 'rb') as f:
                f.read()

            assert mocked_request.call_count >= chunk_count
            assert mocked_request.call_count < 1.2 * chunk_count


def test_file_attribute_cache(ipfs_mounted):
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
    with ipfs_mounted(
        root, ipfs_client,
        attr_cache_size=int(n * 0.9),
    ) as mountpoint:
        subprocess.run(['ls', '-l', mountpoint], **ls_kwargs)
        with request_count_measurement(ipfs_client) as mocked:
            subprocess.run(['ls', '-l', mountpoint], **ls_kwargs)
            assert mocked.call_count >= n

    # now cache size is sufficient
    with ipfs_mounted(
        root, ipfs_client,
        attr_cache_size=int(n * 1.1),
    ) as mountpoint:
        subprocess.run(['ls', '-l', mountpoint], **ls_kwargs)
        with request_count_measurement(ipfs_client) as mocked:
            subprocess.run(['ls', '-l', mountpoint], **ls_kwargs)
            assert mocked.call_count < n * 0.1
