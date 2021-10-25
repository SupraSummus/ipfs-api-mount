import errno
import stat

import pyfuse3

from .high import BaseIPFSOperations


class WholeIPFSOperations(BaseIPFSOperations):
    async def lookup(self, inode, name, ctx):
        if inode == pyfuse3.ROOT_INODE:
            cid = self.ipfs.resolve(name.decode())
            return await self.lookup_cid_or_none(cid, ctx)
        else:
            return await super().lookup(inode, name, ctx)

    async def readdir(self, fh, start_id, token):
        inode = fh
        if inode == pyfuse3.ROOT_INODE:
            raise pyfuse3.FUSEError(errno.EPERM)
        else:
            return await super().readdir(fh, start_id, token)

    async def getattr(self, inode, ctx):
        if inode == pyfuse3.ROOT_INODE:
            attrs = pyfuse3.EntryAttributes()
            attrs.st_ino = inode
            attrs.st_atime_ns = 0
            attrs.st_ctime_ns = 0
            attrs.st_mtime_ns = 0
            attrs.st_gid = 0
            attrs.st_uid = 0
            attrs.st_mode = (
                stat.S_IFDIR |
                stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )
            attrs.st_nlink = 0
            attrs.st_size = 0
            return attrs
        else:
            return await super().getattr(inode, ctx)
