# 4Charm

[![CI](https://github.com/RazorBackRoar/4Charm/actions/workflows/ci.yml/badge.svg)](https://github.com/RazorBackRoar/4Charm/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Apple Silicon](https://img.shields.io/badge/Apple%20Silicon-arm64-brightgreen.svg)](https://support.apple.com/en-us/HT211814)
[![PySide6](https://img.shields.io/badge/PySide6-Qt6-orange.svg)](https://doc.qt.io/qtforpython/)

```text
██╗  ██╗ ██████╗██╗  ██╗ █████╗ ██████╗ ███╗   ███╗
██║  ██║██╔════╝██║  ██║██╔══██╗██╔══██╗████╗ ████║
███████║██║     ███████║███████║██████╔╝██╔████╔██║
╚════██║██║     ██╔══██║██╔══██║██╔══██╗██║╚██╔╝██║
     ██║╚██████╗██║  ██║██║  ██║██║  ██║██║ ╚═╝ ██║
     ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
```

> **High-performance native macOS 4chan media downloader.**
> Download entire threads, catalogs, or boards with intelligent organization, fail-safe resume, and zero duplicates.

---

## Features

- **Bulk Downloading** — queue up to 20 threads or catalogs simultaneously
- **Smart Organization** — automatic folder structure with WEBM separation
- **Fail-Safe Resume** — automatically resumes interrupted downloads
- **Duplicate Prevention** — SHA-256 hashing prevents re-downloading files
- **Rate Limiting** — adaptive throttling with exponential backoff prevents IP bans
- **Download Verification** — MD5 checksum validation ensures file integrity
- **Connection Pooling** — 4× connection pooling for faster concurrent downloads
- **Real-Time Progress** — live bandwidth monitoring with ETA display
- **Apple Silicon Native** — arm64 build optimized for M1/M2/M3/M4 chips

---

## Installation

1. Download the latest `4Charm.dmg` from [Releases](https://github.com/RazorBackRoar/4Charm/releases)
2. Open the DMG and drag `4Charm.app` to `/Applications`
3. First launch — right-click the app → **Open** to bypass Gatekeeper on the ad-hoc signed build

---

## Usage

1. **Add URLs** — paste any 4chan thread, catalog, or board URL
2. **Start** — click Download and watch the live progress log
3. **Enjoy** — files are saved to your chosen download folder with automatic organization

---

## Development

### Requirements

- Python 3.14
- macOS 12.0+
- [uv](https://github.com/astral-sh/uv)

### Setup

```bash
git clone https://github.com/RazorBackRoar/4Charm.git
cd 4Charm
uv sync
uv run python -m four_charm.main
```

### Build

```bash
razorbuild 4Charm
# Output: dist/4Charm.dmg
```

### Lint & Test

```bash
uv run ruff check .
uv run ty check src --python-version 3.14
uv run pytest tests/ -q
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
Copyright © 2026 RazorBackRoar

<!-- razorcore:runtime:start -->
## Runtime Requirements

For users:
- Download the macOS `.dmg` or `.app` release. Python does not need to be installed.

For developers:
- Primary development/build target: Python 3.14 with `uv`.
- Source compatibility goal: Python 3.12-3.14 (best effort).
- Setup: `uv sync`
- Run: `uv run python -m four_charm`
<!-- razorcore:runtime:end -->
