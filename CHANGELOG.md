# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Well, at least this is the intention.

## [Unreleased]
### Added
 * Official support for python 3.9
 * Support for go-ipfs 0.8, 0.9, 0.10

### Changed
 * Switched from fusepy (fuse2) to pyfuse3 (fuse3, low-level).

### Removed
 * Removed `--background` and `--nothreads` options. Now we are always foreground and multithreaded.
 * Dropped support for python 3.6
 * Dropped support for go-ipfs 0.5, 0.6

## [0.4.1] - 2021-03-16
### Fixed
 * Fixed protobuf package version mismatch

## [0.4.0] - 2021-03-16
### Added
 * `--timeout` parameter
 * Support for go-ipfs v0.7.x

## [0.3.3] - 2020-07-28
### Added
 * Mounting whole IPFS namesace at once (`ipfs-api-mount-whole`)
 * Deduplicating daemon requests when using multiple threads - this may improve performance in some multithreaded scenarios
 * Configured tox+pytest test suite with beautiful parametrized test cases

### Fixed
 * More robust support for v1 CIDs

## [0.3.2] - 2020-07-12
### Added
 * Version info embedded in package and available via `--version`
 * Public python-level API for mounting - `ipfs_mounted` context manager

### Removed
 * `IPFSMount` no longer accepts `ready` argument

### Fixed
 * Fixed protobuf package version mismatch
 * CID v1 support

## [0.3.1] - 2020-07-02
### Added
 * Support for go-ipfs v0.5.x and v0.6.x (using ipfshttpclient 0.6.x)
