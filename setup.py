#!/usr/bin/env python
from setuptools import setup
from distutils.command.build import build
from subprocess import check_call


class custom_build(build):
    def run(self):
        if not self.dry_run:
            check_call(['protoc', '--python_out=.', 'unixfs.proto'])
        build.run(self)


setup(
    name='ipfs_api_mount',
    version='1.0',
    description='Mount IPFS directory as local FS.',
    install_requires=[
        'fusepy',
        'ipfsapi',
        'protobuf',
    ],
    setup_requires=[
        'protobuf',
    ],
    scripts=['ipfs_api_mount.py'],
    cmdclass={'build': custom_build},
)
