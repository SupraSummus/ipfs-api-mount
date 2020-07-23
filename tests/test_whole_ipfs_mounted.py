import os
import pytest

from ipfs_api_mount.fuse_operations import WholeIPFSOperations
from ipfs_api_mount import ipfs_mounted

from tools import ipfs_client


def test_cant_list_mountpoint_root(fuse_kwargs):
    with ipfs_mounted(
        ipfs_client,
        fuse_operations_class=WholeIPFSOperations,
        **fuse_kwargs,
    ) as mountpoint:
        # stat indicates only x permission (no read, just enter)
        s = os.stat(mountpoint)
        assert s.st_mode == 0o40111
        # if we try we get PermissionError
        with pytest.raises(PermissionError):
            os.listdir(mountpoint)
