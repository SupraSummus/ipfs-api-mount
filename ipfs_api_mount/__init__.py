from functools import lru_cache
import errno
import os
import stat

import fuse
import ipfshttpclient

from . import unixfs_pb2


class InvalidIPFSPathException(Exception):
    pass


class IPFSMount(fuse.Operations):
    use_ns = True

    def __init__(
        self,
        root,  # root IPFS path
        ipfs_client,  # ipfshttpclient client instance
        ls_cache_size=64,
        object_data_cache_size=256,  # ~256MB assuming 1MB max block size
        object_links_cache_size=256,
        ready=None,  # an event to notify that everything is set-up
    ):
        self.root = root

        # trick to get lrucache use only one arg

        api = ipfs_client

        @lru_cache(maxsize=object_data_cache_size)
        def object_data(object_id):
            try:
                data = unixfs_pb2.Data()
                data.ParseFromString(api.object.data(object_id))
                return data
            except ipfshttpclient.exceptions.StatusError:
                return None

        @lru_cache(maxsize=object_links_cache_size)
        def object_links(object_id):
            try:
                return [
                    l['Hash']
                    for l in api.object.links(object_id).get('Links', [])
                ]
            except ipfshttpclient.exceptions.StatusError:
                return None

        @lru_cache(maxsize=ls_cache_size)
        def ls(object_id):
            return {
                entry['Name']: entry
                for entry in api.ls(object_id)['Objects'][0]['Links']
            }

        self._ls = ls
        self._object_data = object_data
        self._object_links = object_links

        if ready is not None:
            ready.set()

        # this shouldn't be called before `ready` is set because it may throw an exception and hang forever
        self._validate_root_path()

    def _validate_root_path(self):
        if not self._path_is_dir(self.root):
            raise InvalidIPFSPathException("root path is not a directory")

    def _path_type(self, path):
        data = self._object_data(path)
        if data is None:
            return None
        else:
            return data.Type

    def _path_is_dir(self, path):
        return self._path_type(path) in (
            unixfs_pb2.Data.Directory,
            unixfs_pb2.Data.HAMTShard,
        )

    def _path_is_file(self, path):
        return self._path_type(path) in (
            unixfs_pb2.Data.File,
        )

    def _path_exists(self, path):
        return self._path_is_dir(path) or self._path_is_file(path)

    def _path_size(self, path):
        data = self._object_data(path)
        if data is None:
            return None
        else:
            return data.filesize

    def _read_into(self, object_hash, offset, buff):
        """ Read bytes begining at `offset` from given object into
        buffer. Returns end offset of copied data. """

        assert(offset >= 0)

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
        elif not self._path_exists(self.root + path):
            raise fuse.FuseOSError(errno.ENOENT)

        # we dont use file handles so return anthing
        return 0

    def read(self, path, size, offset, fh):
        if self._path_is_dir(self.root + path):
            raise fuse.FuseOSError(errno.EISDIR)
        elif not self._path_is_file(self.root + path):
            raise fuse.FuseOSError(errno.ENOENT)

        data = bytearray(size)
        n = self._read_into(self.root + path, offset, memoryview(data))
        return bytes(data[:(n - offset)])

    def readdir(self, path, fh):
        if not self._path_is_dir(self.root + path):
            raise fuse.FuseOSError(errno.ENOTDIR)

        return ['.', '..'] + list(self._ls(self.root + path).keys())

    def getattr(self, path, fh=None):
        if self._path_is_dir(self.root + path):
            st_mode = stat.S_IFDIR
        elif self._path_is_file(self.root + path):
            st_mode = stat.S_IFREG
        else:
            raise fuse.FuseOSError(errno.ENOENT)

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
