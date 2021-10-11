from unittest import mock
import tempfile

import ipfshttpclient


ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')


def ipfs_file(content, **kwargs):
    # workaround for https://github.com/ipfs/py-ipfs-http-client/issues/187
    with tempfile.NamedTemporaryFile() as f:
        f.write(content)
        f.flush()
        return ipfs_client.add(f.name, **kwargs)['Hash']


def ipfs_dir(contents):
    node = ipfs_client.object.new(template='unixfs-dir')['Hash']
    for name, val in contents.items():
        node = ipfs_client.object.patch.add_link(node, name, val)['Hash']
    return node


def request_count_measurement(client):
    return mock.patch.object(
        ipfshttpclient.http._backend.ClientSync,
        '_request',
        wraps=client._client._request,
    )
