ipfs-api-mount
==============

Mount IPFS directory as local FS.

go-ipfs daemon has this function but as of version 0.4.11 it's slow.
`ipfs-api-mount` aims to be more efficient. For sequential access to
random data it's ~4 times slower than `ipfs cat`.

It's supposed that FS mounted by go-ipfs daemon is slow because of file
structure being accessed in every read. By adding caching one can improve
performance a lot.

How to use
----------

Install package in a virtualenv (or systemwide) and then

    mkdir a_dir
    ipfs-api-mount --background QmXKqqUymTQpEM89M15G23wot8g7n1qVYQQ6vVCpEofYSe a_dir
    ls a_dir
    # aaa  bbb

To unmount

    fusermount -u a_dir

Benchmark
---------

Try it yourself and run `./benchamrk [number of Mbytes]`.

(Benchmark is a bit unfair because files are all zeros. This causes
massive amounts of deduplication and makes cache effects excellent.)

Output at my puny (intel atom, EMMC storage) machine with go-ipfs 0.4.11:

    (venv) [jan@aaa ipfs-api-mount]$ ./benchmark.sh 10
    10MB of zeroes at:
    	QmaJ6kN9fW3TKpVkpf1NuW7cjhHjNp5Jwr3cQuHzsoZWkJ
    	QmYrFyYenMpLxeWZJZqhkwkqjXTdsMqwM82yqzHbKxh7j2/zeroes

    ### ipfs cat QmaJ6kN9fW3TKpVkpf1NuW7cjhHjNp5Jwr3cQuHzsoZWkJ

    real	0m0.346s
    user	0m0.193s
    sys	0m0.134s

    ### ipfs-api-mount QmYrFyYenMpLxeWZJZqhkwkqjXTdsMqwM82yqzHbKxh7j2 /tmp/tmp.NrUuA6pLT6
    ### cat /tmp/tmp.NrUuA6pLT6/zeroes

    real	0m0.136s
    user	0m0.000s
    sys	0m0.015s

    ### cat /ipfs/QmaJ6kN9fW3TKpVkpf1NuW7cjhHjNp5Jwr3cQuHzsoZWkJ

    real	0m6.858s
    user	0m0.000s
    sys	0m0.217s

    (venv) [jan@aaa ipfs-api-mount]$ ./benchmark.sh 100
    100MB of zeroes at:
    	Qmca3PNFKuZnYkiVv1FpcV1AfDUm4qCSHoYjPTBqDAsyk8
    	QmaLb3YYnFMfg7nSsRo2JrQwC52VDZym7EdmNcdbtvTbRM/zeroes

    ### ipfs cat Qmca3PNFKuZnYkiVv1FpcV1AfDUm4qCSHoYjPTBqDAsyk8

    real	0m1.795s
    user	0m0.600s
    sys	0m1.050s

    ### ipfs-api-mount QmaLb3YYnFMfg7nSsRo2JrQwC52VDZym7EdmNcdbtvTbRM /tmp/tmp.r2gkT7qMXN
    ### cat /tmp/tmp.r2gkT7qMXN/zeroes

    real	0m0.740s
    user	0m0.000s
    sys	0m0.096s

    ### cat /ipfs/Qmca3PNFKuZnYkiVv1FpcV1AfDUm4qCSHoYjPTBqDAsyk8
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

Tests
-----

    ./test.sh
