import errno
import logging
import os
import stat

import fuse

from .ipfs import CachedIPFS, InvalidIPFSPathException


logger = logging.getLogger(__name__)


class IPFSMount(fuse.Operations):
    use_ns = True

    def __init__(
        self,
        root,  # root IPFS path
        ipfs_client,  # ipfshttpclient client instance
        ready=None,  # an event to notify that everything is set-up
        **kwargs,
    ):
        self.root = root
        self.ipfs = CachedIPFS(ipfs_client, **kwargs)

        if ready is not None:
            ready.set()

        # this shouldn't be called before `ready` is set because it may throw an exception and hang forever
        self._validate_root_path()

    def _validate_root_path(self):
        if not self.ipfs.path_is_dir(self.root):
            raise InvalidIPFSPathException("root path is not a directory")

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
            if not self.ipfs.path_is_dir(full_path) and not self.ipfs.path_is_file(full_path):
                logger.warning('strange entity type at %s', full_path)
                fuse.FuseOSError(errno.ENOENT)
        except InvalidIPFSPathException as e:
            raise fuse.FuseOSError(errno.ENOENT) from e

        # we dont use file handles so return anything
        return 0

    def read(self, path, size, offset, fh):
        try:
            if self.ipfs.path_is_dir(self.root + path):
                raise fuse.FuseOSError(errno.EISDIR)
            elif not self.ipfs.path_is_file(self.root + path):
                raise fuse.FuseOSError(errno.ENOENT)
        except InvalidIPFSPathException as e:
            raise fuse.FuseOSError(errno.ENOENT) from e

        data = bytearray(size)
        n = self.ipfs.read_into(
            self.ipfs.resolve(self.root + path),
            offset, memoryview(data),
        )
        return bytes(data[:(n - offset)])

    def readdir(self, path, fh):
        ls_result = self.ipfs.ls(self.root + path)
        if ls_result is None:
            raise fuse.FuseOSError(errno.ENOTDIR)

        return ['.', '..'] + list(ls_result.keys())

    def getattr(self, path, fh=None):
        try:
            if self.ipfs.path_is_dir(self.root + path):
                st_mode = (
                    stat.S_IFDIR |
                    stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                )
            elif self.ipfs.path_is_file(self.root + path):
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
            'st_size': self.ipfs.path_size(self.root + path),
        }

    getxattr = None
    listxattr = None


fuse_kwargs = dict(
    auto_unmount=True,
    ro=True,
    kernel_cache=True,
)
