import subprocess

import pytest

import ipfs_api_mount


@pytest.mark.parametrize('script', ['ipfs-api-mount', 'ipfs-api-mount-whole'])
def test_version(script):
    version_string = subprocess.check_output([script, '--version'])
    assert version_string == (script + ' ' + ipfs_api_mount.__version__ + '\n').encode()
