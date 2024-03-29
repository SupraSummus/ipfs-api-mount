#!/usr/bin/env python
from subprocess import check_call

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop


def compile_protobuf():
    check_call(['protoc', '--python_out=.', 'ipfs_api_mount/unixfs.proto'])


class custom_build_py(build_py):
    def run(self):
        if not self.dry_run:
            compile_protobuf()
        build_py.run(self)


class custom_develop(develop):
    def run(self):
        if not self.dry_run:
            compile_protobuf()
        develop.run(self)


exec(open('ipfs_api_mount/version.py').read())


setup(
    name='ipfs_api_mount',
    version=__version__,  # noqa: F821
    description='Mount IPFS directory as local FS.',
    license='MIT',
    url='https://github.com/SupraSummus/ipfs-api-mount',
    classifiers=[
        'Topic :: System :: Filesystems',
    ],
    keywords='ipfs fuse mount fs',
    install_requires=[
        'ipfshttpclient==0.8.0a2',
        'lru-dict==1.*',
        'protobuf>=3.15,<4',
        'py-multibase==1.*',
        'pyfuse3>=3.2.1,<4',
        'trio>=0.19.0,<0.20',
    ],
    packages=find_packages(),
    scripts=[
        'bin/ipfs-api-mount',
        'bin/ipfs-api-mount-whole',
    ],
    package_data={
        'ipfs_api_mount': ['ipfs_api_mount/unixfs.proto'],
    },
    cmdclass={
        'build_py': custom_build_py,
        'develop': custom_develop,
    },
)
