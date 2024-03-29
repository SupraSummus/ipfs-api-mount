import os
from contextlib import contextmanager

import pytest

import ipfs_api_mount
from ipfs_api_mount.fuse_operations import IPFSOperations, WholeIPFSOperations


@pytest.fixture(
    params=[
        {'whole': False},
        {'whole': True},
    ],
)
def ipfs_mounted(request):
    if request.param['whole']:
        @contextmanager
        def f(root, *args, fuse_kwargs=None, **kwargs):
            fuse_operation = WholeIPFSOperations(*args, **kwargs)
            with ipfs_api_mount.ipfs_mounted(
                fuse_operation,
                **(fuse_kwargs or {}),
            ) as mountpoint:
                yield os.path.join(mountpoint, root)
        return f

    else:
        return lambda *args, fuse_kwargs=None, **kwargs: ipfs_api_mount.ipfs_mounted(
            IPFSOperations(*args, **kwargs),
            **(fuse_kwargs or {}),
        )
