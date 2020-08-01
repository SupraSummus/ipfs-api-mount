import logging
import threading
from contextlib import contextmanager

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
        timeout=30.0,  # in seconds
    ):
        self.client = ipfs_client
        self.client_request_kwargs = {
            'timeout': timeout,
        }

        self.resolve_cache = LockingLRU(attr_cache_size)
        self.cid_type_cache = LockingLRU(attr_cache_size)
        self.path_size_cache = LockingLRU(attr_cache_size)
        self.ls_cache = LockingLRU(ls_cache_size)
        self.block_cache = LockingLRU(block_cache_size)
        self.subblock_cids_cache = LockingLRU(link_cache_size)
        self.subblock_sizes_cache = LockingLRU(link_cache_size)

    def resolve(self, path):
        """ Get CID (content id) of a path. """
        with self.resolve_cache.get_or_lock(path) as (in_cache, value):
            if in_cache:
                return value

            try:
                absolute_path = self.client.resolve(path, **self.client_request_kwargs)['Path']
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
        with self.block_cache.get_or_lock(cid) as (in_cache, value):
            if in_cache:
                return value

            if self._is_object(cid):
                # object
                object_data = self._load_object(cid)
                return object_data.Data

            elif self._is_raw_block(cid):
                # raw block
                block = self.client.block.get(cid, **self.client_request_kwargs)
                self.block_cache[cid] = block
                return block

            else:
                # unknown object type
                raise InvalidIPFSPathException()

    def subblock_cids(self, cid):
        """ Get blocks linked from given IPFS object / block """

        if self._is_object(cid):
            # object
            with self.subblock_cids_cache.get_or_lock(cid) as (in_cache, value):
                if in_cache:
                    return value

                subblock_cids = [
                    link['Hash']
                    for link in self.client.object.links(
                        cid,
                        **self.client_request_kwargs,
                    ).get('Links', [])
                ]
                self.subblock_cids_cache[cid] = subblock_cids
                return subblock_cids

        elif self._is_raw_block(cid):
            # raw block - it has no subblocks
            return []

        else:
            # unknown object type
            raise InvalidIPFSPathException()

    def subblock_sizes(self, cid):
        """ Get sizes of blocks linked from given IPFS object / block
        (in the same order as in subblock_cids)
        """

        if self._is_object(cid):
            # object
            with self.subblock_sizes_cache.get_or_lock(cid) as (in_cache, value):
                if in_cache:
                    return value

                object_data = self._load_object(cid)
                return object_data.blocksizes

        elif self._is_raw_block(cid):
            # raw block - it has no subblocks
            return []

        else:
            # unknown object type
            raise InvalidIPFSPathException()

    def ls(self, path):
        with self.ls_cache.get_or_lock(path) as (in_cache, value):
            if in_cache:
                return value

            try:
                ls_result = {
                    entry['Name']: entry
                    for entry in self.client.ls(
                        path,
                        **self.client_request_kwargs,
                    )['Objects'][0]['Links']
                }

            except ipfshttpclient.exceptions.ErrorResponse:
                ls_result = None

            self.ls_cache[path] = ls_result
            return ls_result

    def path_size(self, path):
        cid = self.resolve(path)

        if cid is None:
            return None

        with self.path_size_cache.get_or_lock(cid) as (in_cache, value):
            if in_cache:
                return value

            if self._is_object(cid):
                # object
                object_data = self._load_object(cid)
                return object_data.filesize

            elif self._is_raw_block(cid):
                # raw block
                in_cache, block = self.block_cache.get(cid)
                if in_cache:
                    size = len(block)
                else:
                    size = self.client.block.stat(
                        cid,
                        **self.client_request_kwargs,
                    )['Size']
                self.path_size_cache[cid] = size
                return size

            else:
                # unknown object type
                raise InvalidIPFSPathException()

    def cid_type(self, cid):
        if self._is_object(cid):
            with self.cid_type_cache.get_or_lock(cid) as (in_cache, value):
                if in_cache:
                    return value

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
        """ Get object data and fill relevant caches """
        object_data = unixfs_pb2.Data()
        object_data.ParseFromString(self.client.object.data(
            cid,
            **self.client_request_kwargs,
        ))

        self.cid_type_cache[cid] = object_data.Type
        self.path_size_cache[cid] = object_data.filesize
        self.block_cache[cid] = object_data.Data
        self.subblock_sizes_cache[cid] = object_data.blocksizes

        return object_data

    def _is_object(self, cid):
        if cid.startswith('Q'):
            # v0 object
            return True

        try:
            cid_bytes = multibase.decode(cid)
        except ValueError:
            logger.exception("encountered malformed object/block id")
            return False

        # v1 object
        return cid_bytes.startswith(bytes([0x01, 0x70]))

    def _is_raw_block(self, cid):
        try:
            cid_bytes = multibase.decode(cid)
        except ValueError:
            logger.exception("encountered malformed object/block id")
            return False

        # v1 raw block
        return cid_bytes.startswith(bytes([0x01, 0x55]))


class LockingLRU:
    def __init__(self, *args, **kwargs):
        self.cache = LRU(*args, **kwargs)
        self.global_lock = threading.Lock()
        self.key_events = {}

    def get(self, key):
        while True:
            with self.global_lock:
                if key in self.cache:
                    return True, self.cache[key]
                if key in self.key_events:
                    key_event = self.key_events[key]
                else:
                    return False, None

            key_event.wait()

    @contextmanager
    def get_or_lock(self, key):
        value, event = self._get_value_or_release_event(key)
        if event:
            try:
                yield False, None
            finally:
                with self.global_lock:
                    del self.key_events[key]
                event.set()
        else:
            yield True, value

    def __setitem__(self, key, value):
        with self.global_lock:
            self.cache[key] = value

    def _get_value_or_release_event(self, key):
        while True:
            with self.global_lock:
                if key in self.cache:
                    return self.cache[key], None
                if key in self.key_events:
                    key_event = self.key_events[key]
                else:
                    key_event = threading.Event()
                    self.key_events[key] = key_event
                    return None, key_event

            key_event.wait()
