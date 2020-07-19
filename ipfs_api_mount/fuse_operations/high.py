import errno
import logging
import os
import stat

import fuse
import ipfshttpclient

from ipfs_api_mount.ipfs import CachedIPFS, InvalidIPFSPathException


logger = logging.getLogger(__name__)


class IPFSMount(fuse.Operations):
    use_ns = True

    def __init__(
        self,
        root,  # root IPFS path
        ipfs_client,  # ipfshttpclient client instance
        **kwargs,
    ):
        self.root = root
        self.ipfs = CachedIPFS(ipfs_client, **kwargs)

        self._validate_root_path()

    def _validate_root_path(self):
        if not self.ipfs.path_is_dir(self.root):
            raise InvalidIPFSPathException("root path is not a directory")

    def get_ipfs_path(self, path):
        return self.root + path

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
            full_path = self.get_ipfs_path(path)
            if not self.ipfs.path_is_dir(full_path) and not self.ipfs.path_is_file(full_path):
                logger.warning('strange entity type at %s', full_path)
                fuse.FuseOSError(errno.ENOENT)

        except InvalidIPFSPathException as e:
            raise fuse.FuseOSError(errno.ENOENT) from e

        except ipfshttpclient.exceptions.TimeoutError as e:
            logger.warning('timeout while open(%s)', full_path)
            raise fuse.FuseOSError(errno.EAGAIN) from e

        # we dont use file handles so return anything
        return 0

    def read(self, path, size, offset, fh):
        full_path = self.get_ipfs_path(path)

        try:
            if self.ipfs.path_is_dir(full_path):
                raise fuse.FuseOSError(errno.EISDIR)
            elif not self.ipfs.path_is_file(full_path):
                raise fuse.FuseOSError(errno.ENOENT)

            data = bytearray(size)
            n = self.ipfs.read_into(
                self.ipfs.resolve(full_path),
                offset, memoryview(data),
            )
            return bytes(data[:(n - offset)])

        except InvalidIPFSPathException as e:
            raise fuse.FuseOSError(errno.ENOENT) from e

        except ipfshttpclient.exceptions.TimeoutError as e:
            logger.warning('timeout while read(%s)', full_path)
            raise fuse.FuseOSError(errno.EAGAIN) from e

    def readdir(self, path, fh):
        full_path = self.get_ipfs_path(path)
        try:
            ls_result = self.ipfs.ls(full_path)
        except ipfshttpclient.exceptions.TimeoutError as e:
            logger.warning('timeout while readdir(%s)', full_path)
            raise fuse.FuseOSError(errno.EAGAIN) from e

        if ls_result is None:
            raise fuse.FuseOSError(errno.ENOTDIR)

        return ['.', '..'] + list(ls_result.keys())

    def getattr(self, path, fh=None):
        full_path = self.get_ipfs_path(path)
        try:
            if self.ipfs.path_is_dir(full_path):
                st_mode = (
                    stat.S_IFDIR |
                    stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                )
            elif self.ipfs.path_is_file(full_path):
                st_mode = stat.S_IFREG
            else:
                raise fuse.FuseOSError(errno.ENOENT)

            st_size = self.ipfs.path_size(full_path)

        except InvalidIPFSPathException as e:
            raise fuse.FuseOSError(errno.ENOENT) from e

        except ipfshttpclient.exceptions.TimeoutError as e:
            logger.warning('timeout while getattr(%s)', full_path)
            raise fuse.FuseOSError(errno.EAGAIN) from e

        st_mode |= stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH

        return {
            'st_atime': 0,
            'st_ctime': 0,
            'st_mtime': 0,
            'st_gid': 0,
            'st_uid': 0,
            'st_mode': st_mode,
            'st_nlink': 0,
            'st_size': st_size,
        }

    getxattr = None
    listxattr = None
