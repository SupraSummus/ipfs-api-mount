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

See also
--------

* [Discussion at go-ipfs repo](https://github.com/ipfs/go-ipfs/issues/2166) along with an idea to fix it by adding cache
* [js-ipfs-mount](https://github.com/piedar/js-ipfs-mount) - similar utility, but written in nodejs
