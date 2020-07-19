from contextlib import contextmanager
from threading import Thread
import subprocess
import tempfile
import time

import fuse

from .fuse_operations import IPFSMount, fuse_kwargs


class IPFSMountTimeout(Exception):
    pass


class IPFSFUSEThread(Thread):
    def __init__(
        self,
        mountpoint,
        *fuse_operations_args,
        fuse_operations_class=IPFSMount,
        multithreaded=True,
        max_read=0,  # 0 means default (no read size limit)
        attr_timeout=1.0,  # 1s - default value according to manpage
        **fuse_operations_kwargs,
    ):
        super().__init__()
        self.mountpoint = mountpoint
        self.fuse_operations_class = fuse_operations_class
        self.multithreaded = multithreaded
        self.max_read = max_read
        self.attr_timeout = attr_timeout
        self.fuse_operations_args = fuse_operations_args
        self.fuse_operations_kwargs = fuse_operations_kwargs

    def run(self):
        self.exc = None
        try:
            self.mount()
        except Exception as e:
            self.exc = e

    def join(self):
        super().join()
        if self.exc:
            raise self.exc

    def mount(self):
        ipfs_mount = self.fuse_operations_class(
            *self.fuse_operations_args,
            **self.fuse_operations_kwargs,
        )
        fuse.FUSE(
            ipfs_mount,
            self.mountpoint,
            foreground=True,
            nothreads=not self.multithreaded,
            allow_other=False,
            max_read=self.max_read,
            attr_timeout=self.attr_timeout,
            **fuse_kwargs,
        )

    def unmount(self):
        # TODO - fuse_exit() has global effects, so locking/more precise termination is needed
        # anyway, fuse.fuse_exit() <- causes segafult, so not using it
        subprocess.run(
            ['fusermount', '-u', self.mountpoint, '-q'],
            check=self.is_alive(),  # this command has to succeed only if fuse thread is feeling good
        )

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.unmount()
        self.join()


@contextmanager
def ipfs_mounted(
    *args,
    mount_timeout=5.0,  # seconds
    **kwargs,
):
    with tempfile.TemporaryDirectory() as mountpoint:
        with IPFSFUSEThread(mountpoint, *args, **kwargs) as fuse_thread:

            # dirty dirty active waiting for now
            # no idea how to do it the clean way
            waiting_start = time.monotonic()
            while fuse_thread.is_alive() and not is_mountpoint_ready(mountpoint):
                if time.monotonic() - waiting_start > mount_timeout:
                    raise IPFSMountTimeout()
                time.sleep(0.01)

            # dirty dirty - but sometimes FUSE is not ready immediately, despite being listed in /proc/mounts
            time.sleep(0.1)

            # do wrapped things
            yield mountpoint


def is_mountpoint_ready(mountpoint):
    # AFAIK works only under linux. More platform-agnostic version may come later.
    with open('/proc/mounts', 'rt') as mounts:
        for mount in mounts:
            typ, this_mountpoint, *_ = mount.split(' ')
            if this_mountpoint == mountpoint:
                return True
    return False
