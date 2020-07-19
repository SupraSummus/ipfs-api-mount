import subprocess

import ipfs_api_mount


def test_version():
    version_string = subprocess.check_output(['ipfs-api-mount', '--version'])
    assert version_string == ('ipfs-api-mount ' + ipfs_api_mount.__version__ + '\n').encode()
