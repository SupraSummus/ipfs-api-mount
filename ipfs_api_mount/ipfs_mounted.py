from . import IPFSMount
from contextlib import contextmanager
from threading import Thread, Event
import fuse
import subprocess
import tempfile
import time


@contextmanager
def ipfs_mounted(root, ipfs_client, multithreaded=False, **kwargs):
    with tempfile.TemporaryDirectory() as mountpoint:
        # start fuse thread
        ready = Event()

        def _do_fuse_things():
            fuse.FUSE(
                IPFSMount(
                    root,
                    ipfs_client,
                    ready=ready,
                    **kwargs,
                ),
                mountpoint,
                foreground=True,
                nothreads=not multithreaded,
            )

        fuse_thread = Thread(target=_do_fuse_things)
        fuse_thread.start()
        ready.wait()
        time.sleep(1)  # meh, dirty

        # do wrapped things
        yield mountpoint

        # stop fuse thread
        # TODO - fuse_exit() has global effects, so locking/more precise termination is needed
        # fuse.fuse_exit() <- causes segafult, so not using it
        subprocess.run(['fusermount', '-u', mountpoint], check=True)
        fuse_thread.join()
