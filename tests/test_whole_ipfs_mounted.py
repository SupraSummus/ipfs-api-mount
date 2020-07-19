import os
import pytest

from ipfs_api_mount.fuse_operations import WholeIPFSOperations
from ipfs_api_mount import ipfs_mounted

from tools import ipfs_client, ipfs_dir


@pytest.mark.parametrize('multithreaded', [False, True])
def test_cant_list_mountpoint_root(multithreaded):
    with ipfs_mounted(
        ipfs_client,
        fuse_operations_class=WholeIPFSOperations,
        multithreaded=multithreaded,
    ) as mountpoint:
        # stat indicates only x permission (no read, just enter)
        s = os.stat(mountpoint)
        assert s.st_mode == 0o40111
        # if we try we get PermissionError
        with pytest.raises(PermissionError):
            os.listdir(mountpoint)


@pytest.mark.parametrize('multithreaded', [False, True])
def test_dir_read(multithreaded):
    root = ipfs_dir({
        'a_dir': ipfs_dir({}),
    })
    with ipfs_mounted(
        ipfs_client,
        fuse_operations_class=WholeIPFSOperations,
        multithreaded=multithreaded,
    ) as mountpoint:
        assert os.listdir(os.path.join(mountpoint, root)) == ['a_dir']
