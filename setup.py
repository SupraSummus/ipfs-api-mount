#!/usr/bin/env python
from setuptools import setup
from distutils.command.build import build
from subprocess import check_call


class custom_build(build):
    def run(self):
        if not self.dry_run:
            check_call(['protoc', '--python_out=.', 'ipfs_api_mount/unixfs.proto'])
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
    packages=['ipfs_api_mount'],
    scripts=['bin/ipfs-api-mount'],
    cmdclass={'build': custom_build},
)
