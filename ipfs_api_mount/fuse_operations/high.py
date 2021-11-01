import errno
import logging
import stat
from dataclasses import dataclass

import ipfshttpclient
import pyfuse3

from ipfs_api_mount.ipfs import CachedIPFS, InvalidIPFSPathException


logger = logging.getLogger(__name__)


@dataclass
class IPFSInode:
    cid: str
    ino: int
    lookup_count: int = 0


class BaseIPFSOperations(pyfuse3.Operations):
    def __init__(
        self,
        ipfs_client,  # ipfshttpclient client instance
        **kwargs,
    ):
        self.ipfs = CachedIPFS(ipfs_client, **kwargs)
        self.inodes = {}
        self.inodes_by_cid = {}
        self.inode_free = pyfuse3.ROOT_INODE + 1

    async def lookup(self, inode, name, ctx):
        ipfs_inode = self.inodes[inode]
        child_cid = self.ipfs.resolve(ipfs_inode.cid + '/' + name.decode())
        return await self.lookup_cid_or_none(child_cid, ctx)

    def lookup_cid(self, cid, ctx=None):
        if cid in self.inodes_by_cid:
            ipfs_inode = self.inodes_by_cid[cid]
        else:
            ipfs_inode = IPFSInode(
                ino=self.inode_free,
                cid=cid,
            )
            self.inode_free += 1
            self.inodes[ipfs_inode.ino] = ipfs_inode
            self.inodes_by_cid[ipfs_inode.cid] = ipfs_inode
        ipfs_inode.lookup_count += 1
        return self.getattr(ipfs_inode.ino, ctx)

    async def lookup_cid_or_none(self, cid, ctx=None):
        if cid:
            return await self.lookup_cid(cid, ctx)
        else:
            return pyfuse3.EntryAttributes(st_ino=0)

    async def forget(self, inode_list):
        for inode, n in inode_list:
            ipfs_inode = self.inodes[inode]
            ipfs_inode.lookup_count -= n
            assert ipfs_inode.lookup_count >= 0
            if ipfs_inode.lookup_count == 0:
                del self.inodes[ipfs_inode.ino]
                del self.inodes_by_cid[ipfs_inode.cid]
                del ipfs_inode

    async def open(self, inode, flags, ctx):
        return pyfuse3.FileInfo(fh=inode, keep_cache=True)

    async def read(self, fh, offset, size):
        inode = fh
        cid = self.inodes[inode].cid

        try:
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
        return inode

    async def readdir(self, fh, start_id, token):
        inode = fh
        cid = self.inodes[inode].cid
        try:
            ls_result = self.ipfs.cid_ls(cid)
        except ipfshttpclient.exceptions.TimeoutError as e:
            logger.warning('timeout while readdir(%s)', cid)
            raise pyfuse3.FUSEError(errno.EAGAIN) from e

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
                await self.forget([(entry_attrs.st_ino, 1)])
                return

    async def getattr(self, inode, ctx):
        cid = self.inodes[inode].cid
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
        self.inodes[pyfuse3.ROOT_INODE] = IPFSInode(
            cid=root_cid,
            ino=pyfuse3.ROOT_INODE,
            lookup_count=1,
        )
        self.fsname = f'/ipfs/{root_cid}'
