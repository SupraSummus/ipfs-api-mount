#!/usr/bin/env python
from setuptools import setup
from distutils.command.build import build
from setuptools.command.develop import develop
from subprocess import check_call


def compile_protobuf():
    check_call(['protoc', '--python_out=.', 'ipfs_api_mount/unixfs.proto'])


class custom_build(build):
    def run(self):
        if not self.dry_run:
            compile_protobuf()
        build.run(self)


class custom_develop(develop):
    def run(self):
        if not self.dry_run:
            compile_protobuf()
        develop.run(self)


setup(
    name='ipfs_api_mount',
    version='0.2.0',
    description='Mount IPFS directory as local FS.',
    license='MIT',
    url='https://github.com/SupraSummus/ipfs-api-mount',
    classifiers=[
        'Topic :: System :: Filesystems',
    ],
    keywords='ipfs fuse mount fs',
    install_requires=[
        'fusepy==3.0.*',
        'ipfshttpclient==0.4.*',
        'protobuf==3.6.*',
    ],
    packages=['ipfs_api_mount'],
    scripts=['bin/ipfs-api-mount'],
    package_data={
        'ipfs_api_mount': ['ipfs_api_mount/unixfs.proto'],
    },
    cmdclass={
        'build': custom_build,
        'develop': custom_develop,
    },
)
