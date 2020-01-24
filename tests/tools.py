import ipfshttpclient


api = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')


def ipfs_file(content):
    return api.add_bytes(content)


def ipfs_dir(contents):
    node = api.object.new(template='unixfs-dir')['Hash']
    for name, val in contents.items():
        node = api.object.patch.add_link(node, name, val)['Hash']
    return node
