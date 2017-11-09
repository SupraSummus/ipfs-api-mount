ipfs-api-mount
==============

Mount IPFS directory as local FS.

go-ipfs daemon has this function but as of version 0.4.11 it's slow.
`ipfs-api-mount` aims to be more efficient.

It's supposed that FS mounted by go-ipfs daemon is slow because of file
structure being accessed in every read. By adding caching one can improve
performance a lot.

How to use
----------

Install deps in a virtualenv (or systemwide) and then

    mkdir a_dir
    ./ipfs_api_mount.py QmXKqqUymTQpEM89M15G23wot8g7n1qVYQQ6vVCpEofYSe a_dir
    ls a_dir
    # aaa  bbb

To unmount

    fusermount -u a_dir

Benchmark
---------

Try it yourself and run `./benchamrk [number of Mbytes]`.

Output at my puny (intel atom, EMMC storage) machine with go-ipfs 0.4.11:

    (venv) [jan@aaa ipfs-api-mount]$ ./benchmark.sh 10
    10MB of zeroes at:
    	QmaJ6kN9fW3TKpVkpf1NuW7cjhHjNp5Jwr3cQuHzsoZWkJ
    	QmYrFyYenMpLxeWZJZqhkwkqjXTdsMqwM82yqzHbKxh7j2/zeroes

    ### ipfs cat QmaJ6kN9fW3TKpVkpf1NuW7cjhHjNp5Jwr3cQuHzsoZWkJ

    real	0m0.358s
    user	0m0.205s
    sys	0m0.136s

    ### python ipfs_api_mount.py QmYrFyYenMpLxeWZJZqhkwkqjXTdsMqwM82yqzHbKxh7j2 /tmp/tmp.iL7USPLnnf
    ### cat /tmp/tmp.iL7USPLnnf/zeroes

    real	0m0.523s
    user	0m0.000s
    sys	0m0.015s

    ### cat /ipfs/QmaJ6kN9fW3TKpVkpf1NuW7cjhHjNp5Jwr3cQuHzsoZWkJ

    real	0m7.006s
    user	0m0.000s
    sys	0m0.200s

    (venv) [jan@aaa ipfs-api-mount]$ ./benchmark.sh 100
    100MB of zeroes at:
        Qmca3PNFKuZnYkiVv1FpcV1AfDUm4qCSHoYjPTBqDAsyk8
        QmaLb3YYnFMfg7nSsRo2JrQwC52VDZym7EdmNcdbtvTbRM/zeroes

    ### ipfs cat Qmca3PNFKuZnYkiVv1FpcV1AfDUm4qCSHoYjPTBqDAsyk8

    real	0m1.758s
    user	0m0.609s
    sys	0m1.035s

    ### python ipfs_api_mount.py QmaLb3YYnFMfg7nSsRo2JrQwC52VDZym7EdmNcdbtvTbRM /tmp/tmp.bLG79MLHhS
    ### cat /tmp/tmp.bLG79MLHhS/zeroes

    real	0m7.600s
    user	0m0.000s
    sys	0m0.131s

    ### cat /ipfs/Qmca3PNFKuZnYkiVv1FpcV1AfDUm4qCSHoYjPTBqDAsyk8
    ^C # ... and I'm not patient enough

More in depth description
-------------------------

`ipfs-api-mount` uses both node API and gateway interfaces. Node API is
used for listing directories. Accessing gateway with `Range` header is
then only way to read range from file (AFAIK).

`ipfs-api-mount` uses fixed-size chunk caching. Cache has fixed max size.
In case of multiple parelell reads there is a risk of cache thrashing.
If this occurs performance will be much worst than without cache. When
using the command you can adjust chunk size and cache size to get best
performance.

Tests
-----

    ./test.sh
