import pyfuse3

from .high import IPFSOperations
from .high_whole import WholeIPFSOperations


__all__ = ['IPFSOperations', 'default_fuse_options', 'WholeIPFSOperations']

default_fuse_options = set(pyfuse3.default_options)
default_fuse_options.add('auto_unmount')
default_fuse_options.add('ro')
