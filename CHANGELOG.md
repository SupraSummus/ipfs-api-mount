# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Well, at least this is the intention.

## [Unreleased]
### Added
 * Version info embedded in package and available via `--version`

### Changed
 * Reworked `ipfs_mounted` context manager internals

### Removed
 * `IPFSMount` no longer accepts `ready` argument

### Fixed
 * More liberal requirements for protobuf version - any v3.x.x is now good

## [0.3.1] - 2020-07-02
### Added
 * Support for go-ipfs v0.5.x and v0.6.x (using ipfshttpclient 0.6.x)
