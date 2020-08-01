# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Well, at least this is the intention.

## [Unreleased]
### Added
 * `--timeout` parameter

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
