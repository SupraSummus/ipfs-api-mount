ipfs-api-mount
==============

[![Build Status](https://travis-ci.com/SupraSummus/ipfs-api-mount.svg?branch=master)](https://travis-ci.com/SupraSummus/ipfs-api-mount)
[![codecov](https://codecov.io/gh/SupraSummus/ipfs-api-mount/branch/master/graph/badge.svg)](https://codecov.io/gh/SupraSummus/ipfs-api-mount)

Mount IPFS directory as local FS.

go-ipfs daemon has this function but as of version 0.4.22 it's slow.
`ipfs-api-mount` aims to be more efficient. For sequential access to
random data it's ~3 times slower than `ipfs cat` but also ~20 times
faster than `cat`ing files mounted by go-ipfs.

It's supposed that FS mounted by go-ipfs daemon is slow because of file
structure being accessed in every read. By adding caching one can improve
performance a lot.

How to use
----------

Install package ...

    pip install ipfs-api-mount

... and then

    mkdir a_dir
    ipfs-api-mount --background QmXKqqUymTQpEM89M15G23wot8g7n1qVYQQ6vVCpEofYSe a_dir
    ls a_dir
    # aaa  bbb

To unmount

    fusermount -u a_dir

### Mount whole IPFS at once

Apart from mounting one specified CID you can also mount whole IPFS namespace. This is similar to `ipfs mount` provided in go-ipfs.

    mkdir a_dir
    ipfs-api-mount-whole --background a_dir
    ls a_dir/QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco
    # -  I  index.html  M  wiki

### Python-level use

Mountpoints can be created inside python programs

    import os
    import ipfshttpclient
    from ipfs_api_mount.ipfs_mounted import ipfs_mounted

    with ipfs_mounted('QmSomeHash', ipfshttpclient.connect()) as mountpoint:
        print(os.listdir(mountpoint))

Benchmark
---------

Try it yourself and run `./benchamrk [number of Mbytes]`.

Example output:

    [jan@bubel ipfs-api-mount]$ ./benchmark.sh 10
    ipfs version 0.4.22
    creating 10MB of random data and uploading to ipfs ...
    10MB of data at:
        QmP3YepbcGX8PXST3NYjXDjwAscrD8poT4YA2wJudpea8W
        QmTfmg74kWcmqum1LaJHhK4j7M8GUv1k2XfcQpUPViCe35/data

    ### ipfs cat QmP3YepbcGX8PXST3NYjXDjwAscrD8poT4YA2wJudpea8W

    real	0m0.091s
    user	0m0.024s
    sys	0m0.045s

    ### ipfs-api-mount QmTfmg74kWcmqum1LaJHhK4j7M8GUv1k2XfcQpUPViCe35 /tmp/tmp.Adw8sn8My2
    ### cat /tmp/tmp.Adw8sn8My2/data

    real	0m0.189s
    user	0m0.006s
    sys	0m0.000s

    ### cat /ipfs/QmP3YepbcGX8PXST3NYjXDjwAscrD8poT4YA2wJudpea8W

    real	0m5.949s
    user	0m0.000s
    sys	0m0.084s

More in depth description
-------------------------

`ipfs-api-mount` uses node API for listing directories and reading
objects. Objects are decoded and file structure is created localy (not
in IPFS node). Caching is added on objects level. In case of nonlinear
file access with many small reads there is a risk of cache thrashing.
If this occurs performance will be much worst than without cache. When
using the command you can adjust cache size to get best performance (but
for cache thrashing there is little hope).

Caching options
---------------

There are four cache parameters:
* `--ls-cache-size` - how many directory content lists are cached. Increase this if you want subsequent `ls` to be faster.
* `--block-cache-size` - how many data blocks are cached. This cache needs to be bigger if you are doing sequential reads in many scattered places at once (in single or multiple files). It doesn't affect speed of reading the same spot for the second time, because this is handled by FUSE (`kernel_cache` option). This cache is memory-intensive - takes up to 1MB per entry.
* `--link-cache-size` - Files on IPFS are trees of blocks. This cache keeps the tree structure. Increase this cache's size if you are reading many big files simultanously (depth of a single tree is generally <4, but many of them can overflow the cache). It doesn't affect speed of reading previously read data - this is handled by FUSE (`kernel_cache` option).
* `--attr-cache-size` - cache related to file and directory attributes. This needs to be bigger if you are reading many files attributes, and you want subsequent reads to be faster. For example, if you do `ls -l` (`-l` will call `stat()` on every file) on a large directory and you want second `ls -l` to be faster, you need to set this cache to be bigger than number of files in the directory.

Hope that makes sense ;-)


See also
--------

* [Discussion at go-ipfs repo](https://github.com/ipfs/go-ipfs/issues/2166) along with an idea to fix it by adding cache
* [js-ipfs-mount](https://github.com/piedar/js-ipfs-mount) - similar utility, but written in nodejs
