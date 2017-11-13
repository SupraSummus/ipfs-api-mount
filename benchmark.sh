#!/bin/sh

zeroes=$(dd if=/dev/zero bs=1M count=$1 2>/dev/null | ipfs add --pin=false -Q)
zeroes_in_dir=$(ipfs object patch add-link $(ipfs object new unixfs-dir) zeroes $zeroes)

echo "${1}MB of zeroes at:"
echo -e "\t$zeroes"
echo -e "\t$zeroes_in_dir/zeroes"
echo

echo "### ipfs cat $zeroes"
time { ipfs cat "$zeroes" >/dev/null 2>&1; }
echo

tmp_mnt=$(mktemp -d)
echo "### ipfs-api-mount $zeroes_in_dir $tmp_mnt"
ipfs-api-mount --background "$zeroes_in_dir" "$tmp_mnt"
echo "### cat $tmp_mnt/zeroes"
time cat "$tmp_mnt/zeroes" >/dev/null
fusermount -u "$tmp_mnt"
echo
rmdir "$tmp_mnt"

echo "### cat /ipfs/$zeroes"
time cat "/ipfs/$zeroes" >/dev/null
echo


