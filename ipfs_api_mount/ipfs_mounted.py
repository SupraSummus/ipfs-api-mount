from contextlib import contextmanager
from threading import Thread, Event
import subprocess
import tempfile
import time

import fuse

from . import IPFSMount, fuse_kwargs


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
    multithreaded=True,
    max_read=0,  # 0 means default (no read size limit)
    attr_timeout=1.0,  # 1s - default value according to manpage
    **kwargs,
):
    with tempfile.TemporaryDirectory() as mountpoint:
        # start fuse thread
        ready = Event()

        def _do_fuse_things():
            fuse.FUSE(
                # Funny thing - IPFSMount has to be constructed here. Assigning is to local var break things.
                IPFSMount(
                    *args,
                    ready=ready,
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
        if not ready.wait(timeout=5):
            if fuse_thread.exc is not None:
                raise fuse_thread.exc
            assert False  # panic, basically
        time.sleep(1)  # this is dirty, but after setting `ready` fuse thread does few other things - we give it some time here

        try:
            # do wrapped things
            yield mountpoint

        finally:
            # stop fuse thread
            # TODO - fuse_exit() has global effects, so locking/more precise termination is needed
            # anyway, fuse.fuse_exit() <- causes segafult, so not using it
            subprocess.run(
                ['fusermount', '-u', mountpoint],
                check=fuse_thread.exc is None,  # this command has to succeed only if fuse thread is feeling good
            )
            fuse_thread.join()
