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


class MeasuringHTTPClient(ipfshttpclient.http.HTTPClient):
    def __init__(self, *args, **kwargs):
        self.request_count = 0
        return super().__init__(*args, **kwargs)

    def _do_request(self, *args, **kwargs):
        self.request_count += 1
        return super()._do_request(*args, **kwargs)


class MeasuringClient(ipfshttpclient.Client):
    _clientfactory = MeasuringHTTPClient

    @property
    def request_count(self):
        return self._client.request_count

    def clear_request_count(self):
        self._client.request_count = 0
