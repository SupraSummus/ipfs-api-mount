from unittest import mock
import errno
import os
import subprocess

import pytest
import ipfshttpclient

import ipfs_api_mount
from ipfs_api_mount.ipfs import InvalidIPFSPathException

from tools import ipfs_client, ipfs_dir, ipfs_file


@pytest.mark.parametrize('entries', [[], ['aaa', 'bbb']])
def test_dir_read(ipfs_mounted, entries):
    root = ipfs_dir({
        name: ipfs_dir({})
        for name in entries
    })
    with ipfs_mounted(
        root, ipfs_client,
    ) as mountpoint:
        assert sorted(os.listdir(mountpoint)) == sorted(entries)


def test_file_times(ipfs_mounted):
    """creation/modification/access times for a file are all 0"""
    root = ipfs_dir({
        'bbb': ipfs_file(b'blabla'),
    })
    with ipfs_mounted(
        root, ipfs_client,
    ) as mountpoint:
        s = os.stat(os.path.join(mountpoint, 'bbb'))
        assert s.st_ctime == 0
        assert s.st_mtime == 0
        assert s.st_atime == 0


def test_permission(ipfs_mounted):
    root = ipfs_dir({})
    with ipfs_mounted(
        root, ipfs_client,
    ) as mountpoint:
        s = os.stat(mountpoint)
        assert s.st_mode == 0o40555


def test_permission_nested(ipfs_mounted):
    root = ipfs_dir({
        'dir': ipfs_dir({}),
    })
    with ipfs_mounted(
        root, ipfs_client,
    ) as mountpoint:
        s = os.stat(os.path.join(mountpoint, 'dir'))
        assert s.st_mode == 0o40555


def test_cid_version_1(ipfs_mounted):
    # constant cid because i'm lazy
    root = "bafybeiczsscdsbs7ffqz55asqdf3smv6klcw3gofszvwlyarci47bgf354"
    with ipfs_mounted(
        root, ipfs_client,
    ) as mountpoint:
        assert os.listdir(mountpoint) == []


@pytest.mark.parametrize('content', [
    b'I forgot newline at the end. Oops.',
    10 * 1024 * 1024,
])
@pytest.mark.parametrize('raw_leaves', [False, True])
def test_small_file_read(ipfs_mounted, content, raw_leaves):
    # apparently you can't pass large things via parametrize
    if isinstance(content, int):
        content = os.urandom(content)
    root = ipfs_dir({'file': ipfs_file(content, raw_leaves=raw_leaves)})
    with ipfs_mounted(
        root, ipfs_client,
    ) as mountpoint:
        with open(os.path.join(mountpoint, 'file'), 'rb') as f:
            assert f.read() == content


def test_cid_version_1_small_file(ipfs_mounted):
    content = "this is next gen file"
    root = subprocess.run(
        f'echo "{content}" | ipfs add --cid-version 1 --wrap-with-directory --quieter --stdin-name file',
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout.decode('ascii').strip()
    with ipfs_mounted(
        root, ipfs_client,
    ) as mountpoint:
        with open(os.path.join(mountpoint, 'file'), 'rb') as f:
            assert f.read().decode('ascii') == content + '\n'


def test_invalid_root_hash(fuse_kwargs):
    """ we should refuse to mount invalid hash """
    with pytest.raises(InvalidIPFSPathException):
        with ipfs_api_mount.ipfs_mounted(
            'straight/to/nonsense', ipfs_client,
            **fuse_kwargs,
        ):
            pass


def test_file_root_hash(fuse_kwargs):
    """ we should refuse to mount something that is a file (dir is needed) """
    root = ipfs_file(b'definetly not a dir')
    with pytest.raises(InvalidIPFSPathException):
        with ipfs_api_mount.ipfs_mounted(
            root, ipfs_client,
            **fuse_kwargs,
        ):
            pass


def test_complex_root_hash(ipfs_mounted):
    root = ipfs_dir({
        'nested_dir': ipfs_dir({
            'empty_dir': ipfs_dir({}),
        }),
    })
    with ipfs_mounted(
        root + '/nested_dir', ipfs_client,
    ) as mountpoint:
        assert os.listdir(mountpoint) == ['empty_dir']


def test_nonexistent_file(ipfs_mounted):
    """ there is no way we can open nonexistent file """
    root = ipfs_dir({})
    with ipfs_mounted(
        root, ipfs_client,
    ) as mountpoint:
        with pytest.raises(FileNotFoundError):
            open(os.path.join(mountpoint, 'a_file'), 'rb')


def test_timeout_while_read(ipfs_mounted):
    root = ipfs_dir({
        'a_file': ipfs_file(b'blabla\n')
    })
    with ipfs_mounted(
        root, ipfs_client,
        timeout=0.123,
    ) as mountpoint:
        with open(os.path.join(mountpoint, 'a_file'), 'rb') as f:
            fd = f.fileno()

            # timeout error is signaled
            with mock.patch.object(
                ipfshttpclient.http.ClientSync,
                '_request',
                side_effect=ipfshttpclient.exceptions.TimeoutError(None),
            ) as _request_mocked:
                with pytest.raises(OSError) as excinfo:
                    os.read(fd, 1)
            assert excinfo.value.errno == errno.EAGAIN

            # timeout value is passed to client
            _request_mocked.assert_called()
            for call in _request_mocked.call_args_list:
                call.kwargs['timeout'] == 0.123

            # without timeouted request there is no error
            os.read(fd, 1)
