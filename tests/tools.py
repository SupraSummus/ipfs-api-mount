import tempfile

import ipfshttpclient


api = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')


def ipfs_file(content):
    # workaround for https://github.com/ipfs/py-ipfs-http-client/issues/187
    with tempfile.NamedTemporaryFile() as f:
        f.write(content)
        f.flush()
        return api.add(f.name)['Hash']


def ipfs_dir(contents):
    node = api.object.new(template='unixfs-dir')['Hash']
    for name, val in contents.items():
        node = api.object.patch.add_link(node, name, val)['Hash']
    return node
