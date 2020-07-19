from .high import IPFSMount
from .high_whole import WholeIPFSOperations


__all__ = ['IPFSMount', 'fuse_kwargs', 'WholeIPFSOperations']


fuse_kwargs = dict(
    auto_unmount=True,
    ro=True,
    kernel_cache=True,
)
