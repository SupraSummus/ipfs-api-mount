from functools import lru_cache
import errno
import logging
import os
import stat

import fuse
import ipfshttpclient
import multibase

from . import unixfs_pb2


logger = logging.getLogger(__name__)


class InvalidIPFSPathException(Exception):
    pass


class IPFSMount(fuse.Operations):
    use_ns = True

    def __init__(
        self,
        root,  # root IPFS path
        ipfs_client,  # ipfshttpclient client instance
        ls_cache_size=64,
        object_data_cache_size=256,  # 2 * ~256MB assuming 1MB max block size
        object_links_cache_size=256,
        ready=None,  # an event to notify that everything is set-up
    ):
        self.root = root

        # trick to get lrucache use only one arg

        api = ipfs_client

        @lru_cache(maxsize=1024 * 10)
        def resolve_path(object_path):
            try:
                absolute_path = api.resolve(object_path)['Path']

            except ipfshttpclient.exceptions.ErrorResponse as e:
                raise InvalidIPFSPathException(
                    "couldn't resolve object at path {}".format(object_path),
                ) from e

            except ipfshttpclient.exceptions.TimeoutError as e:
                logger.warning('timeout while resolving path %s', object_path)
                raise fuse.FuseOSError(errno.EAGAIN) from e

            if not absolute_path.startswith('/ipfs/'):
                raise InvalidIPFSPathException()
            return absolute_path[6:]

        @lru_cache(maxsize=object_data_cache_size)
        def object_data(object_id):
            try:
                data = unixfs_pb2.Data()
                data.ParseFromString(api.object.data(object_id))
                return data

            except ipfshttpclient.exceptions.ErrorResponse:
                return None

            except ipfshttpclient.exceptions.TimeoutError:
                logger.warning('timeout while reading object data %s', object_id)
                raise fuse.FuseOSError(errno.EAGAIN)

        @lru_cache(maxsize=object_data_cache_size)
        def block_data(cid):
            try:
                return api.block.get(cid)

            except ipfshttpclient.exceptions.ErrorResponse as e:
                raise InvalidIPFSPathException() from e

            except ipfshttpclient.exceptions.TimeoutError as e:
                logger.warning('timeout while reading block %s', cid)
                raise fuse.FuseOSError(errno.EAGAIN) from e

        @lru_cache(maxsize=1024 * 10)
        def block_size(cid):
            try:
                return api.block.stat(cid)['Size']

            except ipfshttpclient.exceptions.ErrorResponse as e:
                raise InvalidIPFSPathException() from e

            except ipfshttpclient.exceptions.TimeoutError as e:
                logger.warning('timeout while doing stat for block %s', cid)
                raise fuse.FuseOSError(errno.EAGAIN) from e

        @lru_cache(maxsize=object_links_cache_size)
        def object_links(object_id):
            try:
                return [
                    l['Hash']
                    for l in api.object.links(object_id).get('Links', [])
                ]

            except ipfshttpclient.exceptions.ErrorResponse:
                return None

            except ipfshttpclient.exceptions.TimeoutError:
                logger.warning('timeout while reading object links %s', object_id)
                raise fuse.FuseOSError(errno.EAGAIN)

        @lru_cache(maxsize=ls_cache_size)
        def ls(object_path):
            try:
                return {
                    entry['Name']: entry
                    for entry in api.ls(object_path)['Objects'][0]['Links']
                }

            except ipfshttpclient.exceptions.ErrorResponse:
                return None

            except ipfshttpclient.exceptions.TimeoutError:
                logger.warning('timeout while doing ls for %s', object_path)
                raise fuse.FuseOSError(errno.EAGAIN)

        self._resolve_path = resolve_path
        self._ls = ls
        self._object_data = object_data
        self._block_data = block_data
        self._block_size = block_size
        self._object_links = object_links

        if ready is not None:
            ready.set()

        # this shouldn't be called before `ready` is set because it may throw an exception and hang forever
        self._validate_root_path()

    def _validate_root_path(self):
        if not self._path_is_dir(self.root):
            raise InvalidIPFSPathException("root path is not a directory")

    def _object_type(self, object_id):
        data = self._object_data(object_id)
        if data is None:
            return None
        else:
            return data.Type

    def _is_raw_block(self, cid):
        try:
            cid_bytes = multibase.decode(cid)
        except ValueError:
            logger.exception("encountered malformed object/block id")
            return False

        return cid_bytes.startswith(bytes([0x01, 0x55]))

    def _path_is_dir(self, path):
        cid = self._resolve_path(path)
        return self._object_type(cid) in (
            unixfs_pb2.Data.Directory,
            unixfs_pb2.Data.HAMTShard,
        )

    def _path_is_file(self, path):
        cid = self._resolve_path(path)
        if cid.startswith('Q'):
            # v0 object
            return self._object_type(cid) in (
                unixfs_pb2.Data.File,
            )

        return self._is_raw_block(cid)

    def _path_size(self, path):
        cid = self._resolve_path(path)

        if cid.startswith('Q'):
            # v0 object
            data = self._object_data(cid)
            if data is None:
                return None
            else:
                return data.filesize

        if self._is_raw_block(cid):
            # v1 raw block
            return self._block_size(cid)

        # unknown object type
        raise InvalidIPFSPathException()

    def _read_into(self, object_hash, offset, buff):
        """ Read bytes begining at `offset` from given object/raw into
        buffer. Returns end offset of copied data. """

        assert(offset >= 0)

        if object_hash.startswith('Q'):
            # this is an v0 object
            return self._read_object_into(object_hash, offset, buff)

        if self._is_raw_block(object_hash):
            # this is a v1 raw leaf
            return self._read_raw_into(object_hash, offset, buff)

        logger.warning("unknown type of object (cid %s)", object_hash)
        return offset

    def _read_raw_into(self, block_id, offset, buff):
        size = len(buff)
        data = self._block_data(block_id)[offset:(offset + size)]
        n = len(data)
        buff[:n] = data
        return offset + n

    def _read_object_into(self, object_hash, offset, buff):
        data = self._object_data(object_hash)
        size = len(buff)

        # missing object
        if data is None:
            return offset

        # only files and raw type objects contains data
        if data.Type in [unixfs_pb2.Data.Raw, unixfs_pb2.Data.File]:
            end = offset

            # copy data contained in this object
            d = data.Data[offset:(offset + size)]
            n = len(d)
            buff[0:n] = d
            end += n

            # copied all requested data?
            if size <= n:
                return end

            # descend into child objects
            block_offset = len(data.Data)
            for blocksize, child_hash in zip(
                data.blocksizes,
                self._object_links(object_hash),
            ):
                if offset + size <= block_offset:
                    # current block is past requested range
                    break
                elif block_offset + blocksize <= offset:
                    # current block is before requested range
                    pass
                else:
                    end = self._read_into(
                        child_hash,
                        max(0, offset - block_offset),
                        buff[(end - offset):(end - offset + blocksize)],
                    ) + block_offset

                # update offset to next block
                block_offset += blocksize

            return end

        # every other thing is empty
        return offset

    def open(self, path, flags):
        write_flags = (
            os.O_WRONLY |
            os.O_RDWR |
            os.O_APPEND |
            os.O_CREAT |
            os.O_EXCL |
            os.O_TRUNC
        )
        if (flags & write_flags) != 0:
            raise fuse.FuseOSError(errno.EROFS)

        try:
            full_path = self.root + path
            if not self._path_is_dir(full_path) and not self._path_is_file(full_path):
                logger.warning('strange entity type at %s', full_path)
                fuse.FuseOSError(errno.ENOENT)
        except InvalidIPFSPathException as e:
            raise fuse.FuseOSError(errno.ENOENT) from e

        # we dont use file handles so return anthing
        return 0

    def read(self, path, size, offset, fh):
        try:
            if self._path_is_dir(self.root + path):
                raise fuse.FuseOSError(errno.EISDIR)
            elif not self._path_is_file(self.root + path):
                raise fuse.FuseOSError(errno.ENOENT)
        except InvalidIPFSPathException as e:
            raise fuse.FuseOSError(errno.ENOENT) from e

        data = bytearray(size)
        n = self._read_into(
            self._resolve_path(self.root + path),
            offset, memoryview(data),
        )
        return bytes(data[:(n - offset)])

    def readdir(self, path, fh):
        ls_result = self._ls(self.root + path)
        if ls_result is None:
            raise fuse.FuseOSError(errno.ENOTDIR)

        return ['.', '..'] + list(ls_result.keys())

    def getattr(self, path, fh=None):
        try:
            if self._path_is_dir(self.root + path):
                st_mode = stat.S_IFDIR
            elif self._path_is_file(self.root + path):
                st_mode = stat.S_IFREG
            else:
                raise fuse.FuseOSError(errno.ENOENT)
        except InvalidIPFSPathException as e:
            raise fuse.FuseOSError(errno.ENOENT) from e

        st_mode |= stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH

        return {
            'st_atime': 0,
            'st_ctime': 0,
            'st_mtime': 0,
            'st_gid': 0,
            'st_uid': 0,
            'st_mode': st_mode,
            'st_nlink': 0,
            'st_size': self._path_size(self.root + path),
        }

    getxattr = None
    listxattr = None
