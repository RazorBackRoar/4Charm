# Changelog

All notable changes to 4Charm will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2026-07-12

### Security
- **Redirect allowlisting:** Media and API fetches follow redirects manually and block hops outside known 4chan/4cdn hosts
- **Narrowed App Transport Security:** Replaced blanket `NSAllowsArbitraryLoads` with explicit exception domains for `4chan.org`, `4channel.org`, `4cdn.org`, and `github.com`

### Changed
- Outbound HTTP helpers live in `transport/session.py` (`safe_get`) and are used by the scraper for all network calls

## [4.12.0] - 2026-04-03

### Added
- **MD5 Verification**: Automatic file integrity checking using checksums from 4chan API
  - Validates downloaded files match expected MD5 hash
  - Automatically retries on verification failure
  - Prevents corrupted downloads from being saved
- **Real-Time Bandwidth Monitoring**: Live download speed tracking with ETA display
  - Shows current download speed in MB/s or KB/s
  - Displays estimated time remaining (seconds, minutes, or hours)
  - Tracks peak download speed during session
- **Enhanced Error Messages**: User-friendly error messages with actionable guidance
  - Clear explanations for connection errors, timeouts, and HTTP errors
  - Specific suggestions for fixing common issues
  - Better disk space and permission error handling
- **Comprehensive Test Suite**: 39 new unit tests covering all new features
  - Bandwidth monitor tests (15 tests)
  - Retry logic tests (10 tests)
  - MD5 verification tests (14 tests)

### Changed
- **Optimized Connection Pooling**: Increased pool size from 2x to 4x workers (10 → 20 connections)
  - 10-20% faster concurrent downloads
  - Better connection reuse across multiple requests
  - Manual retry control for improved error handling
- **Smarter Retry Logic**: Exponential backoff with jitter
  - Prevents thundering herd when multiple downloads fail simultaneously
  - Random jitter (0-1 second) spreads retries over time
  - Maximum delay cap at 60 seconds
- **Adaptive Chunk Sizing**: Memory-efficient streaming based on file size
  - Small files (<10MB): 8KB chunks
  - Medium files (10-100MB): 64KB chunks
  - Large files (≥100MB): 256KB chunks
  - Reduces memory usage and improves throughput

### Fixed
- Retry delays now use exponential backoff instead of fixed delays
- Connection pool properly sized for concurrent download workload
- Progress display now shows ETA for better user visibility

## [4.11.8] - 2026-01-28

### Changed
- Updated dependencies and build configuration
- Improved workspace integration

## [4.11.7] - 2026-01-20

### Added
- Initial public release
- Native macOS app with PySide6 (Qt6)
- Bulk downloading (up to 20 threads/catalogs)
- Smart folder organization with WEBM separation
- Fail-safe resume capability
- SHA-256 duplicate prevention
- Adaptive rate limiting
- Apple Silicon optimization

[2.0.1]: https://github.com/RazorBackRoar/4Charm/releases/tag/v2.0.1
[4.12.0]: https://github.com/RazorBackRoar/4Charm/compare/v4.11.8...v4.12.0
[4.11.8]: https://github.com/RazorBackRoar/4Charm/compare/v4.11.7...v4.11.8
[4.11.7]: https://github.com/RazorBackRoar/4Charm/releases/tag/v4.11.7
