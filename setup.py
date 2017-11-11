#!/usr/bin/env python
from setuptools import setup


setup(
    name='ipfs_api_mount',
    version='1.0',
    description='Mount IPFS directory as local FS.',
    install_requires=[
        'fusepy',
        'ipfsapi',
    ],
    scripts=['ipfs_api_mount.py'],
)
