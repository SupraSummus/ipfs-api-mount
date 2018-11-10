ipfs-api-mount
==============

[![Build Status](https://travis-ci.com/SupraSummus/ipfs-api-mount.svg?branch=master)](https://travis-ci.com/SupraSummus/ipfs-api-mount)
[![codecov](https://codecov.io/gh/SupraSummus/ipfs-api-mount/branch/master/graph/badge.svg)](https://codecov.io/gh/SupraSummus/ipfs-api-mount)

Mount IPFS directory as local FS.

go-ipfs daemon has this function but as of version 0.4.15 it's slow.
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

Output at my puny (intel atom, EMMC storage) machine with go-ipfs 0.4.15:

    [jan@aaa ipfs-api-mount]$ ./benchmark.sh 10
    creating 10MB of random data and uploading to ipfs ...
    10MB of data at:
        Qmbum4ndB5qsGid7FK6t2LSzrzmr3SoXytncR7xLaAFmAj
        Qmbnkzrpx8gDz72iL3yKkHuZKtvNDJacg4gaeNgV97fAUn/data

    ### ipfs cat Qmbum4ndB5qsGid7FK6t2LSzrzmr3SoXytncR7xLaAFmAj

    real	0m0.524s
    user	0m0.195s
    sys	0m0.182s

    ### ipfs-api-mount Qmbnkzrpx8gDz72iL3yKkHuZKtvNDJacg4gaeNgV97fAUn /tmp/tmp.M9dyRJfZcp
    ### cat /tmp/tmp.M9dyRJfZcp/data

    real	0m1.046s
    user	0m0.001s
    sys	0m0.019s

    ### cat /ipfs/Qmbum4ndB5qsGid7FK6t2LSzrzmr3SoXytncR7xLaAFmAj

    real	0m20.062s
    user	0m0.001s
    sys	0m0.192s

    [jan@aaa ipfs-api-mount]$ ./benchmark.sh 100
    creating 100MB of random data and uploading to ipfs ...
    100MB of data at:
        QmPZA3FEoW6FF4by9hdy9ic5PRkHac3dFLsfdhpjCafmGt
        QmWx4dpofRWLKswogzQUvAzX6oi6nEd9fMMe5AD23ECHy1/data

    ### ipfs cat QmPZA3FEoW6FF4by9hdy9ic5PRkHac3dFLsfdhpjCafmGt

    real	0m3.907s
    user	0m0.718s
    sys	0m1.322s

    ### ipfs-api-mount QmWx4dpofRWLKswogzQUvAzX6oi6nEd9fMMe5AD23ECHy1 /tmp/tmp.OGyZXMNSwV
    ### cat /tmp/tmp.OGyZXMNSwV/data

    real	0m9.575s
    user	0m0.000s
    sys	0m0.171s

    ### cat /ipfs/QmPZA3FEoW6FF4by9hdy9ic5PRkHac3dFLsfdhpjCafmGt
    ^C # ... and I'm not patient enough

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
