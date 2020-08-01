import argparse
import logging
import socket
import sys

import fuse
import ipfshttpclient

from . import __version__
from .fuse_operations import IPFSMount, fuse_kwargs, WholeIPFSOperations


class Command:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description=self.get_description())
        self.add_optional_arguments()
        self.add_positional_arguments()

    def get_description(self):
        raise NotImplementedError()

    def add_optional_arguments(self):
        parser = self.parser
        parser.add_argument('--ls-cache-size', type=int, default=64, help='Max number of ls results kept in cache.')
        parser.add_argument('--block-cache-size', type=int, default=16, help='Max number of data blocks kept in cache.')
        parser.add_argument('--link-cache-size', type=int, default=256, help='Max number of object link sections kept in cache.')
        parser.add_argument('--attr-cache-size', type=int, default=1024 * 128, help='Max number of file attributes kept in cache.')
        parser.add_argument('-b', '--background', action='store_true', help='Run in background.')
        parser.add_argument('--no-threads', action='store_true', help='Use single thread to handle FS requests.')
        parser.add_argument('--allow-other', action='store_true', help='Set fuse mount option \'allow_other\'')
        parser.add_argument('--api-host', type=str, default='127.0.0.1', help='IPFS API host')
        parser.add_argument('--api-port', type=int, default=5001, help='IPFS API port')
        parser.add_argument('--timeout', type=float, default=30.0, help='Timeout for daemon requests, in seconds')
        parser.add_argument(
            "-l", "--log",
            dest='log', default=sys.stderr, type=argparse.FileType('w'),
            help="where to put logs, use something like /proc/self/fd/5 for logging to custom fd",
        )
        parser.add_argument(
            "-v", "--verbose",
            dest='verbose_count', action='count', default=0,
            help="increases log verbosity for each occurrence",
        )
        parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)

    def add_positional_arguments(self):
        self.parser.add_argument('mountpoint', type=str, help='Local mountpoint path.')

    def run(self):
        args = self.parser.parse_args()

        # Sets log level to WARN going more verbose for each new -v.
        logging.basicConfig(
            format='%(process)d %(levelname)s: %(message)s',
            level=max(3 - args.verbose_count, 0) * 10,
            stream=args.log,
        )

        logging.info('starting ipfs-api-mount %s with commandline %s', __version__, str(sys.argv))

        ip = socket.gethostbyname(args.api_host)

        with ipfshttpclient.connect(
            '/ip4/{}/tcp/{}/http'.format(ip, args.api_port)
        ) as client:
            fuse.FUSE(
                self.get_fuse_operations_instance(args, client),
                args.mountpoint,
                foreground=not args.background,
                nothreads=args.no_threads,
                allow_other=args.allow_other,
                **fuse_kwargs,
            )

    def get_fuse_operations_kwargs(self, args):
        return dict(
            ls_cache_size=args.ls_cache_size,
            block_cache_size=args.block_cache_size,
            link_cache_size=args.link_cache_size,
            attr_cache_size=args.attr_cache_size,
            timeout=args.timeout,
        )

    def get_fuse_operations_instance(self, args):
        raise NotImplementedError()


class IPFSApiMountCommand(Command):
    def get_description(self):
        return 'Mount specified IPFS directory as local FS.'

    def add_positional_arguments(self):
        self.parser.add_argument('root', type=str, help='Hash of IPFS dir to be mounted.')
        super().add_positional_arguments()

    def get_fuse_operations_instance(self, args, ipfs_client):
        return IPFSMount(
            args.root,
            ipfs_client,
            **self.get_fuse_operations_kwargs(args),
        )


class IPFSApiMountWholeCommand(Command):
    def get_description(self):
        return 'Mount whole IPFS namespace in local directory.'

    def get_fuse_operations_instance(self, args, ipfs_client):
        return WholeIPFSOperations(
            ipfs_client,
            **self.get_fuse_operations_kwargs(args),
        )
