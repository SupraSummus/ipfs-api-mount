from contextlib import contextmanager
from threading import Thread, Event
import subprocess
import tempfile
import time

import fuse

from . import IPFSMount


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
def ipfs_mounted(*args, multithreaded=False, **kwargs):
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
                auto_unmount=True,
                ro=False,
                allow_other=False,
            )

        fuse_thread = ThreadWithException(target=_do_fuse_things)
        fuse_thread.start()
        ready.wait()
        time.sleep(1)  # meh, dirty

        # do wrapped things
        yield mountpoint

        # stop fuse thread
        # TODO - fuse_exit() has global effects, so locking/more precise termination is needed
        # anyway, fuse.fuse_exit() <- causes segafult, so not using it
        subprocess.run(
            ['fusermount', '-u', mountpoint],
            check=fuse_thread.exc is None,  # this command has to succeed only if fuse thread is feeling good
        )
        fuse_thread.join()
