from contextlib import contextmanager
from threading import Thread
import subprocess
import tempfile
import time

import fuse

from . import IPFSMount, fuse_kwargs


class IPFSMountTimeout(Exception):
    pass


class ThreadWithException(Thread):

    def run(self):
        self.exc = None
        try:
            super().run()
        except Exception as e:
            self.exc = e

    def join(self):
        super().join()
        if self.exc:
            raise self.exc


@contextmanager
def ipfs_mounted(
    *args,
    mount_timeout=5.0,  # seconds
    multithreaded=True,
    max_read=0,  # 0 means default (no read size limit)
    attr_timeout=1.0,  # 1s - default value according to manpage
    **kwargs,
):
    with tempfile.TemporaryDirectory() as mountpoint:
        # start fuse thread

        def _do_fuse_things():
            fuse.FUSE(
                # Funny thing - IPFSMount has to be constructed here. Assigning is to local var break things.
                IPFSMount(
                    *args,
                    **kwargs,
                ),
                mountpoint,
                foreground=True,
                nothreads=not multithreaded,
                allow_other=False,
                max_read=max_read,
                attr_timeout=attr_timeout,
                **fuse_kwargs,
            )

        fuse_thread = ThreadWithException(target=_do_fuse_things)
        fuse_thread.start()

        try:
            # dirty dirty active waiting for now
            # no idea how to do it the clean way
            waiting_start = time.monotonic()
            while fuse_thread.is_alive() and not is_mountpoint_ready(mountpoint):
                if time.monotonic() - waiting_start > mount_timeout:
                    raise IPFSMountTimeout()
                time.sleep(0.01)

            # do wrapped things
            yield mountpoint

        finally:
            # stop fuse thread
            # TODO - fuse_exit() has global effects, so locking/more precise termination is needed
            # anyway, fuse.fuse_exit() <- causes segafult, so not using it
            subprocess.run(
                ['fusermount', '-u', mountpoint, '-q'],
                check=fuse_thread.is_alive(),  # this command has to succeed only if fuse thread is feeling good
            )
            fuse_thread.join()


def is_mountpoint_ready(mountpoint):
    # AFAIK works only under linux. More platform-agnostic version may come later.
    with open('/proc/mounts', 'rt') as mounts:
        for mount in mounts:
            typ, this_mountpoint, *_ = mount.split(' ')
            if this_mountpoint == mountpoint:
                return True
    return False
