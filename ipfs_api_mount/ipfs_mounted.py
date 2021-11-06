import subprocess
import tempfile
import time
from contextlib import contextmanager
from threading import Thread

import pyfuse3
import trio

from .fuse_operations import default_fuse_options


class IPFSMountTimeout(Exception):
    pass


class IPFSFUSEThread(Thread):
    def __init__(
        self,
        mountpoint,
        fuse_operations,
        max_read=None,
        allow_other=False,
    ):
        super().__init__()
        self.mountpoint = mountpoint
        self.fuse_operations = fuse_operations
        self.max_read = max_read
        self.allow_other = allow_other

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
        pyfuse3.init(self.fuse_operations, self.mountpoint, self.get_fuse_options())
        try:
            trio.run(pyfuse3.main)
        except Exception:
            pyfuse3.close(unmount=False)
            raise
        else:
            pyfuse3.close()

    def get_fuse_options(self):
        fuse_options = set(default_fuse_options)
        fuse_options.add(f'fsname={self.fuse_operations.fsname}')
        if self.max_read is not None:
            fuse_options.add(f'max_read={self.max_read}')
        if self.allow_other:
            fuse_options.add('allow_other')
        return fuse_options

    def unmount(self, check=None):
        # TODO - unmount using pyfuse3.terimnate()
        if check is None:
            self.is_alive()  # unmounting has to succeed only if fuse thread is feeling good
        subprocess.run(
            ['fusermount3', '-u', self.mountpoint, '-q'],
            check=check,
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
