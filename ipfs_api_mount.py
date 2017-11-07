#!/usr/bin/env python

import errno
import sys
import os
import stat
from functools import lru_cache

import fuse
import ipfsapi
import requests


TYPE_FILE = 2
TYPE_DIR = 1


class IPFSMount(fuse.Operations):

    def __init__(self,
        root, # root IPFS path
        api_host='127.0.0.1', api_port=5001,
        gateway_host='127.0.0.1', gateway_port=8080,
        ls_cache_size=256,
        chunk_size=8*1024*1024, # 8MB
        chunk_cache_size=32, # up to 256MB
    ):
        api = ipfsapi.connect(api_host, api_port)
        gateway = requests.Session()

        self.chunk_size = chunk_size

        # trick to get lrucache use only one arg

        @lru_cache(maxsize=ls_cache_size)
        def ls(path):
            full_path = os.path.join('/ipfs', root + path)
            return {
                entry['Name']: entry
                for entry in api.ls(full_path)['Objects'][0]['Links']
            }

        @lru_cache(maxsize=chunk_cache_size)
        def read_chunk(path, chunk):
            response = gateway.get(
                'http://{}:{}{}'.format(
                    gateway_host,
                    gateway_port,
                    os.path.join('/ipfs', root + path),
                ),
                headers={
                    'Range': 'bytes={}-{}'.format(
                        chunk * chunk_size,
                        (chunk + 1) * chunk_size - 1,
                    ),
                },
            )
            response.raise_for_status()
            return response.content

        def stat(path):
            if path == '/':
                return {
                    'Type': TYPE_DIR,
                    'Size': 0, # a little lie
                }
            head, tail = os.path.split(path)
            return ls(head).get(tail)

        def path_type(path):
            s = stat(path)
            if s is None:
                return None
            else:
                return s.get('Type')

        def path_size(path):
            s = stat(path)
            if s is None:
                return None
            else:
                return s.get('Size')

        self._ls = ls
        self._read_chunk = read_chunk
        self._path_type = path_type
        self._path_size = path_size

    def open(self, path, flags):
        if self._path_type(path) in (TYPE_DIR, TYPE_FILE):
            # we dont use file handles so return anthing
            return 0
        else:
            raise fuse.FuseOSError(errno.ENOENT)

    def read(self, path, size, offset, fh):
        if self._path_type(path) != TYPE_FILE:
            raise fuse.FuseOSError(errno.EISDIR)

        chunks = []
        while size > 0:
            chunk = offset // self.chunk_size
            start = offset % self.chunk_size
            end = start + size
            chunk_data = self._read_chunk(path, chunk)[start:end]
            chunks.append(chunk_data)
            if len(chunk_data) == 0:
                break
            size -= len(chunk_data)
            offset += len(chunk_data)

        return b''.join(chunks)

    def readdir(self, path, fh):
        if self._path_type(path) != TYPE_DIR:
            raise fuse.FuseOSError(errno.ENOTDIR)

        return ['.', '..'] + list(self._ls(path).keys())

    def getattr(self, path, fh=None):
        if self._path_type(path) not in (TYPE_DIR, TYPE_FILE):
            raise fuse.FuseOSError(errno.ENOENT)

        return {
            'st_atime': 0,
            'st_ctime': 0,
            'st_mtime': 0,
            'st_gid': 0,
            'st_uid': 0,
            'st_mode': {
                TYPE_FILE: stat.S_IFREG,
                TYPE_DIR: stat.S_IFDIR,
            }[self._path_type(path)],
            'st_nlink': 0,
            'st_size': self._path_size(path),
        }

    getxattr = None
    listxattr = None


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Mount specified IPFS directory as local FS.')
    parser.add_argument('--chunk-size', type=int, default=8*1024*1024, help='Cached chunk size in bytes.')
    parser.add_argument('--chunk-cache-size', type=int, default=32, help='Max number of chunks kept in cache.')
    parser.add_argument('--ls-cache-size', type=int, default=256, help='Max number of ls results kept in cache.')
    parser.add_argument('--foreground', action='store_true', help='Remain in foreground.')
    parser.add_argument('root', type=str, help='Hash of IPFS dir to be mounted.')
    parser.add_argument('mountpoint', type=str, help='Local mountpoint path.')

    args = parser.parse_args()

    fuse.FUSE(
        IPFSMount(
            args.root,
            chunk_size=args.chunk_size,
            chunk_cache_size=args.chunk_cache_size,
            ls_cache_size=args.ls_cache_size,
        ),
        args.mountpoint,
        foreground=args.foreground,
    )
