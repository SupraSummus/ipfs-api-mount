import os
import subprocess

import pytest

from ipfs_api_mount import InvalidIPFSPathException
from ipfs_api_mount.ipfs_mounted import ipfs_mounted

from tools import ipfs_client, ipfs_dir, ipfs_file


@pytest.mark.parametrize('entries', [[], ['aaa', 'bbb']])
@pytest.mark.parametrize('multithreaded', [False, True])
def test_dir_read(entries, multithreaded):
    root = ipfs_dir({
        name: ipfs_dir({})
        for name in entries
    })
    with ipfs_mounted(
        root, ipfs_client,
        multithreaded=multithreaded,
    ) as mountpoint:
        assert sorted(os.listdir(mountpoint)) == sorted(entries)


@pytest.mark.parametrize('multithreaded', [False, True])
def test_file_times(multithreaded):
    """creation/modification/access times for a file are all 0"""
    root = ipfs_dir({
        'bbb': ipfs_file(b'blabla'),
    })
    with ipfs_mounted(
        root, ipfs_client,
        multithreaded=multithreaded,
    ) as mountpoint:
        s = os.stat(os.path.join(mountpoint, 'bbb'))
        assert s.st_ctime == 0
        assert s.st_mtime == 0
        assert s.st_atime == 0


@pytest.mark.parametrize('multithreaded', [False, True])
def test_permission(multithreaded):
    root = ipfs_dir({})
    with ipfs_mounted(
        root, ipfs_client,
        multithreaded=multithreaded,
    ) as mountpoint:
        s = os.stat(mountpoint)
        assert s.st_mode == 0o40555


@pytest.mark.parametrize('multithreaded', [False, True])
def test_permission_nested(multithreaded):
    root = ipfs_dir({
        'dir': ipfs_dir({}),
    })
    with ipfs_mounted(
        root, ipfs_client,
        multithreaded=multithreaded,
    ) as mountpoint:
        s = os.stat(os.path.join(mountpoint, 'dir'))
        assert s.st_mode == 0o40555


@pytest.mark.parametrize('multithreaded', [False, True])
def test_cid_version_1(multithreaded):
    # constant cid because i'm lazy
    root = "bafybeiczsscdsbs7ffqz55asqdf3smv6klcw3gofszvwlyarci47bgf354"
    with ipfs_mounted(
        root, ipfs_client,
        multithreaded=multithreaded,
    ) as mountpoint:
        assert os.listdir(mountpoint) == []


@pytest.mark.parametrize('content', [
    b'I forgot newline at the end. Oops.',
    10 * 1024 * 1024,
])
@pytest.mark.parametrize('raw_leaves', [False, True])
@pytest.mark.parametrize('multithreaded', [False, True])
def test_small_file_read(content, raw_leaves, multithreaded):
    # apparently you can't pass large things via parametrize
    if isinstance(content, int):
        content = os.urandom(content)
    root = ipfs_dir({'file': ipfs_file(content, raw_leaves=raw_leaves)})
    with ipfs_mounted(
        root, ipfs_client,
        multithreaded=multithreaded,
    ) as mountpoint:
        with open(os.path.join(mountpoint, 'file'), 'rb') as f:
            assert f.read() == content


@pytest.mark.parametrize('multithreaded', [False, True])
def test_cid_version_1_small_file(multithreaded):
    content = "this is next gen file"
    root = subprocess.run(
        f'echo "{content}" | ipfs add --cid-version 1 --wrap-with-directory --quieter --stdin-name file',
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout.decode('ascii').strip()
    with ipfs_mounted(
        root, ipfs_client,
        multithreaded=multithreaded,
    ) as mountpoint:
        with open(os.path.join(mountpoint, 'file'), 'rb') as f:
            assert f.read().decode('ascii') == content + '\n'


@pytest.mark.parametrize('multithreaded', [False, True])
def test_invalid_root_hash(multithreaded):
    """ we should refuse to mount invalid hash """
    with pytest.raises(InvalidIPFSPathException):
        with ipfs_mounted(
            'straight/to/nonsense', ipfs_client,
            multithreaded=multithreaded,
        ):
            pass


@pytest.mark.parametrize('multithreaded', [False, True])
def test_file_root_hash(multithreaded):
    """ we should refuse to mount something that is a file (dir is needed) """
    root = ipfs_file(b'definetly not a dir')
    with pytest.raises(InvalidIPFSPathException):
        with ipfs_mounted(
            root, ipfs_client,
            multithreaded=multithreaded,
        ):
            pass


@pytest.mark.parametrize('multithreaded', [False, True])
def test_complex_root_hash(multithreaded):
    root = ipfs_dir({
        'nested_dir': ipfs_dir({
            'empty_dir': ipfs_dir({}),
        }),
    })
    with ipfs_mounted(
        root + '/nested_dir', ipfs_client,
        multithreaded=multithreaded,
    ) as mountpoint:
        assert os.listdir(mountpoint) == ['empty_dir']


@pytest.mark.parametrize('multithreaded', [False, True])
def test_nonexistent_file(multithreaded):
    """ there is no way we can open nonexistent file """
    root = ipfs_dir({})
    with ipfs_mounted(
        root, ipfs_client,
        multithreaded=multithreaded,
    ) as mountpoint:
        with pytest.raises(FileNotFoundError):
            open(os.path.join(mountpoint, 'a_file'), 'rb')
