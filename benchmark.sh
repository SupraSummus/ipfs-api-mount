#!/bin/sh

# abort on any error
set -e

ipfs version

echo "creating ${1}MB of random data and uploading to ipfs ..."

data=$(dd if=/dev/urandom bs=1M count=$1 2>/dev/null | ipfs add --pin=false -Q)
data_in_dir=$(ipfs object patch add-link $(ipfs object new unixfs-dir) data $data)

echo "${1}MB of data at:"
echo -e "\t$data"
echo -e "\t$data_in_dir/data"
echo

echo "### ipfs cat $data"
time { ipfs cat "$data" >/dev/null 2>&1; }
echo

tmp_mnt=$(mktemp -d)
echo "### ipfs-api-mount $data_in_dir $tmp_mnt"
ipfs-api-mount --background "$data_in_dir" "$tmp_mnt"
echo "### cat $tmp_mnt/data"
time cat "$tmp_mnt/data" >/dev/null
fusermount -u "$tmp_mnt"
echo
rmdir "$tmp_mnt"

echo "### cat /ipfs/$data"
time cat "/ipfs/$data" >/dev/null
echo


