import os
import pytest

from ipfs_api_mount.fuse_operations import WholeIPFSOperations
from ipfs_api_mount import ipfs_mounted

from tools import ipfs_client


def test_cant_list_mountpoint_root():
    with ipfs_mounted(
        WholeIPFSOperations(ipfs_client),
    ) as mountpoint:
        # stat indicates only x permission (no read, just enter)
        s = os.stat(mountpoint)
        assert s.st_mode == 0o40111
        # if we try we get PermissionError
        with pytest.raises(PermissionError):
            os.listdir(mountpoint)


def test_cant_stat_malformed_cid():
    with ipfs_mounted(
        WholeIPFSOperations(ipfs_client),
    ) as mountpoint:
        with pytest.raises(FileNotFoundError):
            os.stat(os.path.join(mountpoint, 'QmSomeHash'))
