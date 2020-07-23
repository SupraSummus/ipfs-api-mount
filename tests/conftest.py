from contextlib import contextmanager
import os

import pytest

import ipfs_api_mount
from ipfs_api_mount.fuse_operations import WholeIPFSOperations

"""
def dict_product(*dict_options):
    for dicts in product(dict_options):
        result_dict = {}
        for d in dicts:
            result_dict.update(d)
        yield result_dict
"""


@pytest.fixture(
    params=[
        {'multithreaded': False},
        {'multithreaded': True},
    ],
)
def fuse_kwargs(request):
    return request.param


@pytest.fixture(
    params=[
        {'whole': False},
        {'whole': True},
    ],
)
def ipfs_mounted(request, fuse_kwargs):
    if request.param['whole']:
        @contextmanager
        def f(root, *args, **kwargs):
            with ipfs_api_mount.ipfs_mounted(
                *args,
                fuse_operations_class=WholeIPFSOperations,
                **fuse_kwargs,
                **kwargs,
            ) as mountpoint:
                yield os.path.join(mountpoint, root)
        return f

    else:
        return lambda *args, **kwargs: ipfs_api_mount.ipfs_mounted(
            *args,
            **fuse_kwargs,
            **kwargs,
        )
