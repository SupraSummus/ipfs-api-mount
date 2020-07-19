from .high import IPFSMount


__all__ = ['IPFSMount', 'fuse_kwargs']


fuse_kwargs = dict(
    auto_unmount=True,
    ro=True,
    kernel_cache=True,
)
