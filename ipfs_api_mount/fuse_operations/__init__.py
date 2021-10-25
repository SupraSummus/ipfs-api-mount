from .high import IPFSOperations
from .high_whole import WholeIPFSOperations


__all__ = ['IPFSOperations', 'fuse_kwargs', 'WholeIPFSOperations']


fuse_kwargs = dict(
    auto_unmount=True,
    ro=True,
    kernel_cache=True,
)
