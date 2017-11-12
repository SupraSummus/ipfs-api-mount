#!/bin/sh

function cleanup {
	fusermount -u "$tmp_mnt" || true
	rmdir "$tmp_mnt" || true
}
trap cleanup EXIT

tmp_mnt=$(mktemp -d)
python ipfs_api_mount.py --background "$1" "$tmp_mnt"

new_hash=$(ipfs add -r -Q --pin=false "$tmp_mnt")

if [ "$new_hash" != "$1" ]; then
	echo "$new_hash != $1"
	exit 1
fi
