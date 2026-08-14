# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.2] - 2026-08-14

### Fixed

- Oversized on-disk files are quarantined and restored if re-download does not succeed
- Quarantine/restore I/O failures are logged

### Added

- Architecture guide and expanded download-pipeline tests

## [2.0.1] - 2026-07-12

### Security

- Redirect allowlisting for API and media downloads (`safe_get`)
- Narrowed macOS App Transport Security exception domains

### Changed

- Capped PySide6 below v7 to prevent silent dependency breakage.

## [1.0.0] - 2024-12-10

### Added

- Initial release
