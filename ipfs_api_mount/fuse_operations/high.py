import errno
import logging
import os
import stat

import ipfshttpclient
import pyfuse3

from ipfs_api_mount.ipfs import CachedIPFS, InvalidIPFSPathException


logger = logging.getLogger(__name__)


class BaseIPFSOperations(pyfuse3.Operations):
    def __init__(
        self,
        ipfs_client,  # ipfshttpclient client instance
        **kwargs,
    ):
        self.ipfs = CachedIPFS(ipfs_client, **kwargs)
        self.inode_cids = {}
        self.cid_inodes = {}
        self.inode_free = pyfuse3.ROOT_INODE + 1

    async def lookup(self, inode, name, ctx):
        cid = self.inode_cids[inode]
        child_cid = self.ipfs.resolve(cid + '/' + name.decode())
        return await self.lookup_cid_or_none(child_cid, ctx)

    def lookup_cid(self, cid, ctx=None):
        if cid in self.cid_inodes:
            inode = self.cid_inodes[cid]
        else:
            inode = self.inode_free
            self.inode_free += 1
            self.inode_cids[inode] = cid
            self.cid_inodes[cid] = inode
        return self.getattr(inode, ctx)

    async def lookup_cid_or_none(self, cid, ctx=None):
        if cid:
            return await self.lookup_cid(cid, ctx)
        else:
            return pyfuse3.EntryAttributes(st_ino=0)

    async def open(self, inode, flags, ctx):
        write_flags = (
            os.O_WRONLY |
            os.O_RDWR |
            os.O_APPEND |
            os.O_CREAT |
            os.O_EXCL |
            os.O_TRUNC
        )
        if (flags & write_flags) != 0:
            raise pyfuse3.FUSEError(errno.EROFS)

        cid = self.inode_cids[inode]
        try:
            if self.ipfs.cid_is_dir(cid):
                raise pyfuse3.FUSEError(errno.EISDIR)
            if not self.ipfs.cid_is_file(cid):
                logger.warning('strange entity type at %s', cid)
                pyfuse3.FUSEError(errno.ENOENT)

        except ipfshttpclient.exceptions.TimeoutError as e:
            logger.warning('timeout while open(%s)', cid)
            raise pyfuse3.FUSEError(errno.EAGAIN) from e

        return pyfuse3.FileInfo(fh=inode, keep_cache=True)

    async def read(self, fh, offset, size):
        inode = fh
        cid = self.inode_cids[inode]

        try:
            if self.ipfs.cid_is_dir(cid):
                raise pyfuse3.FUSEError(errno.EISDIR)
            elif not self.ipfs.cid_is_file(cid):
                raise pyfuse3.FUSEError(errno.ENOENT)

            data = bytearray(size)
            n = self.ipfs.read_into(
                cid,
                offset, memoryview(data),
            )
            return bytes(data[:(n - offset)])

        except ipfshttpclient.exceptions.TimeoutError as e:
            logger.warning('timeout while read(%s)', cid)
            raise pyfuse3.FUSEError(errno.EAGAIN) from e

    async def opendir(self, inode, ctx):
        # TODO check if this is a dir
        return inode

    async def readdir(self, fh, start_id, token):
        inode = fh
        cid = self.inode_cids[inode]
        try:
            ls_result = self.ipfs.cid_ls(cid)
        except ipfshttpclient.exceptions.TimeoutError as e:
            logger.warning('timeout while readdir(%s)', cid)
            raise pyfuse3.FUSEError(errno.EAGAIN) from e

        if ls_result is None:
            raise pyfuse3.FUSEError(errno.ENOTDIR)

        ls_result = ls_result[start_id:]

        for i, entry in enumerate(ls_result):
            entry_name = entry['Name'].encode()
            entry_cid = entry['Hash']
            entry_attrs = await self.lookup_cid(entry_cid)
            r = pyfuse3.readdir_reply(
                token,
                entry_name, entry_attrs,
                start_id + i + 1,
            )
            if not r:
                return

    async def getattr(self, inode, ctx):
        cid = self.inode_cids[inode]
        try:
            if self.ipfs.cid_is_dir(cid):
                st_mode = (
                    stat.S_IFDIR |
                    stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                )
            elif self.ipfs.cid_is_file(cid):
                st_mode = stat.S_IFREG
            else:
                raise pyfuse3.FUSEError(errno.ENOENT)

            st_size = self.ipfs.cid_size(cid)

        except ipfshttpclient.exceptions.TimeoutError as e:
            logger.warning('timeout while getattr(%s)', cid)
            raise pyfuse3.FUSEError(errno.EAGAIN) from e

        st_mode |= stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH

        attrs = pyfuse3.EntryAttributes()
        attrs.st_ino = inode
        attrs.st_atime_ns = 0
        attrs.st_ctime_ns = 0
        attrs.st_mtime_ns = 0
        attrs.st_gid = 0
        attrs.st_uid = 0
        attrs.st_mode = st_mode
        attrs.st_nlink = 0
        attrs.st_size = st_size
        return attrs


class IPFSOperations(BaseIPFSOperations):
    def __init__(
        self,
        root,  # root IPFS path
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        root_cid = self.ipfs.resolve(root)
        if not self.ipfs.cid_is_dir(root_cid):
            raise InvalidIPFSPathException("root path is not a directory")
        self.inode_cids[pyfuse3.ROOT_INODE] = root_cid
