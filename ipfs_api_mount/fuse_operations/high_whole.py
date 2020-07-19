import errno
import stat

import fuse

from .high import IPFSMount


class WholeIPFSOperations(IPFSMount):
    def __init__(self, *args, **kwargs):
        super().__init__(
            None,  # root - we are not using it
            *args,
            **kwargs,
        )

    # Perfect solution would be to extract common base class,
    # and implement this method only in IPFSMount. But for now we have this dirty patching.
    def _validate_root_path(self):
        pass

    def get_ipfs_path(self, path):
        return path[1:]  # strip leading slash

    def readdir(self, path, fh):
        if path == '/':
            raise fuse.FuseOSError(errno.EPERM)
        else:
            return super().readdir(path, fh)

    def getattr(self, path, fh=None):
        if path == '/':
            st_mode = (
                stat.S_IFDIR |
                stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )
            return {
                'st_atime': 0,
                'st_ctime': 0,
                'st_mtime': 0,
                'st_gid': 0,
                'st_uid': 0,
                'st_mode': st_mode,
                'st_nlink': 0,
                'st_size': 0,
            }
        else:
            return super().getattr(path, fh=fh)
