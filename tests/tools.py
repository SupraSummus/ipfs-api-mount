import ipfsapi


host = 'localhost'
port = '5001'
api = ipfsapi.connect(host, port)


def ipfs_file(content):
    return api.add_bytes(content)


def ipfs_dir(contents):
    node = api.object_new(template='unixfs-dir')['Hash']
    for name, val in contents.items():
        node = api.object_patch_add_link(node, name, val)['Hash']
    return node
