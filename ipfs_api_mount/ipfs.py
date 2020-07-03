import logging

from lru import LRU
import ipfshttpclient
import multibase

from . import unixfs_pb2


logger = logging.getLogger(__name__)


class InvalidIPFSPathException(Exception):
    pass


class CachedIPFS:

    def __init__(
        self,
        ipfs_client,  # ipfshttpclient client instance
        attr_cache_size=1024 * 128,
        ls_cache_size=64,
        block_cache_size=16,  # ~16MB assuming 1MB max block size
        link_cache_size=256,
    ):
        self.client = ipfs_client

        self.resolve_cache = LRU(attr_cache_size)
        self.cid_type_cache = LRU(attr_cache_size)
        self.path_size_cache = LRU(attr_cache_size)
        self.ls_cache = LRU(ls_cache_size)
        self.block_cache = LRU(block_cache_size)
        self.subblock_cids_cache = LRU(link_cache_size)
        self.subblock_sizes_cache = LRU(link_cache_size)

    def resolve(self, path):
        """ Get CID (content id) of a path. """
        if path in self.resolve_cache:
            return self.resolve_cache[path]

        try:
            absolute_path = self.client.resolve(path)['Path']
        except ipfshttpclient.exceptions.ErrorResponse:
            absolute_path = None

        if absolute_path is None or not absolute_path.startswith('/ipfs/'):
            self.resolve_cache[path] = None
            return None

        cid = absolute_path[6:]
        self.resolve_cache[path] = cid
        return cid

    def block(self, cid):
        """ Get payload of IPFS object or raw block """
        if cid in self.block_cache:
            return self.block_cache[cid]

        if self._is_v0_object(cid):
            # v0 object
            object_data = self._load_object(cid)
            return object_data.Data

        elif self._is_raw_block(cid):
            # v1 raw block
            block = self.client.block.get(cid)
            self.block_cache[cid] = block
            return block

        else:
            # unknown object type
            raise InvalidIPFSPathException()

    def subblock_cids(self, cid):
        """ Get blocks linked from given IPFS object / block """

        if self._is_v0_object(cid):
            # v0 object
            if cid in self.subblock_cids_cache:
                return self.subblock_cids_cache[cid]

            subblock_cids = [
                link['Hash']
                for link in self.client.object.links(cid).get('Links', [])
            ]
            self.subblock_cids_cache[cid] = subblock_cids
            return subblock_cids

        elif self._is_raw_block(cid):
            # v1 raw block - it has no subblocks
            return []

        else:
            # unknown object type
            raise InvalidIPFSPathException()

    def subblock_sizes(self, cid):
        """ Get sizes of blocks linked from given IPFS object / block
        (in the same order as in subblock_cids)
        """

        if self._is_v0_object(cid):
            # v0 object
            if cid in self.subblock_sizes_cache:
                return self.subblock_sizes_cache[cid]

            object_data = self._load_object(cid)
            return object_data.blocksizes

        elif self._is_raw_block(cid):
            # v1 raw block - it has no subblocks
            return []

        else:
            # unknown object type
            raise InvalidIPFSPathException()

    def ls(self, path):
        if path in self.ls_cache:
            return self.ls_cache[path]

        try:
            ls_result = {
                entry['Name']: entry
                for entry in self.client.ls(path)['Objects'][0]['Links']
            }

        except ipfshttpclient.exceptions.ErrorResponse:
            ls_result = None

        self.ls_cache[path] = ls_result
        return ls_result

    def path_size(self, path):
        cid = self.resolve(path)

        if cid is None:
            return None

        if cid in self.path_size_cache:
            return self.path_size_cache[cid]

        if self._is_v0_object(cid):
            # v0 object
            object_data = self._load_object(cid)
            return object_data.filesize

        elif self._is_raw_block(cid):
            # v1 raw block
            if cid in self.block_cache:
                size = len(self.block_cache[cid])
            else:
                size = self.client.block.stat(cid)['Size']
            self.path_size_cache[cid] = size
            return size

        else:
            # unknown object type
            raise InvalidIPFSPathException()

    def cid_type(self, cid):
        if self._is_v0_object(cid):
            if cid in self.cid_type_cache:
                return self.cid_type_cache[cid]

            object_data = self._load_object(cid)
            return object_data.Type

        elif self._is_raw_block(cid):
            return unixfs_pb2.Data.Raw

        else:
            raise InvalidIPFSPathException()

    def path_is_dir(self, path):
        cid = self.resolve(path)

        if cid is None:
            return False

        return self.cid_type(cid) in (
            unixfs_pb2.Data.Directory,
            unixfs_pb2.Data.HAMTShard,
        )

    def path_is_file(self, path):
        cid = self.resolve(path)

        if cid is None:
            return False

        return self.cid_type(cid) in (
            unixfs_pb2.Data.File,
            unixfs_pb2.Data.Raw,
        )

    def read_into(self, cid, offset, buff):
        """ Read bytes begining at `offset` from given object/raw into
        buffer. Returns end offset of copied data. """
        size = len(buff)

        end = offset

        # copy data contained in this object
        d = self.block(cid)[offset:(offset + size)]
        n = len(d)
        buff[0:n] = d
        end += n

        # copied all requested data?
        if size <= n:
            return end

        # descend into child objects
        block_offset = len(self.block(cid))
        for blocksize, child_hash in zip(
            self.subblock_sizes(cid),
            self.subblock_cids(cid),
        ):
            if offset + size <= block_offset:
                # current block is past requested range
                break
            elif block_offset + blocksize <= offset:
                # current block is before requested range
                pass
            else:
                end = self.read_into(
                    child_hash,
                    max(0, offset - block_offset),
                    buff[(end - offset):(end - offset + blocksize)],
                ) + block_offset

            # update offset to next block
            block_offset += blocksize

        return end

    def _load_object(self, cid):
        """ Get v0 object data and fill relevant caches """
        object_data = unixfs_pb2.Data()
        object_data.ParseFromString(self.client.object.data(cid))

        self.cid_type_cache[cid] = object_data.Type
        self.path_size_cache[cid] = object_data.filesize
        self.block_cache[cid] = object_data.Data
        self.subblock_sizes_cache[cid] = object_data.blocksizes

        return object_data

    def _is_v0_object(self, cid):
        return cid.startswith('Q')

    def _is_raw_block(self, cid):
        try:
            cid_bytes = multibase.decode(cid)
        except ValueError:
            logger.exception("encountered malformed object/block id")
            return False

        return cid_bytes.startswith(bytes([0x01, 0x55]))
