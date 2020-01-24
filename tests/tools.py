import tempfile

import ipfshttpclient


ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')


def ipfs_file(content):
    # workaround for https://github.com/ipfs/py-ipfs-http-client/issues/187
    with tempfile.NamedTemporaryFile() as f:
        f.write(content)
        f.flush()
        return ipfs_client.add(f.name)['Hash']


def ipfs_dir(contents):
    node = ipfs_client.object.new(template='unixfs-dir')['Hash']
    for name, val in contents.items():
        node = ipfs_client.object.patch.add_link(node, name, val)['Hash']
    return node
