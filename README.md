# 4Charm

[![Download](https://img.shields.io/github/v/release/RazorBackRoar/4Charm?style=for-the-badge&label=Download%20DMG&color=d32f2f)](https://github.com/RazorBackRoar/4Charm/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/RazorBackRoar/4Charm/ci.yml?branch=main&style=for-the-badge&label=CI)](https://github.com/RazorBackRoar/4Charm/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blueviolet?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.14-2ea44f?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-Qt6-41cd52?style=for-the-badge&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![macOS](https://img.shields.io/badge/mac%20os-Apple%20Silicon-d32f2f?style=for-the-badge&logo=apple&logoColor=white)](https://support.apple.com/en-us/HT211814)

**High-performance native macOS 4chan media downloader.**

Download entire threads, catalogs, or boards with intelligent organization, fail-safe resume, and zero duplicates.

<p align="center">
  <a href="https://github.com/RazorBackRoar/4Charm/releases/latest/download/4Charm.dmg"><strong>↓ Download 4Charm.dmg</strong></a>
  ·
  <a href="https://github.com/RazorBackRoar/4Charm/releases">All releases</a>
</p>

![4Charm](docs/screenshots/app.png)

## Features

- **Bulk Downloading** — queue up to 20 threads or catalogs simultaneously
- **Smart Organization** — automatic folder structure with WEBM separation
- **Fail-Safe Resume** — automatically resumes interrupted downloads
- **Duplicate Prevention** — SHA-256 hashing prevents re-downloading files
- **Rate Limiting** — adaptive throttling with exponential backoff prevents IP bans
- **Download Verification** — MD5 checksum validation ensures file integrity
- **Redirect Allowlisting** — outbound fetches stay on 4chan/4cdn hosts even across redirects
- **Connection Pooling** — 4× connection pooling for faster concurrent downloads
- **Real-Time Progress** — live bandwidth monitoring with ETA display
- **Apple Silicon Native** — arm64 build optimized for M-series Macs

---

## Platform requirements

- macOS 12.0+ on Apple Silicon (arm64)
- No Python install required for the packaged `.dmg` / `.app`

---

## Install

1. Download [`4Charm.dmg`](https://github.com/RazorBackRoar/4Charm/releases/latest/download/4Charm.dmg)
2. Open the DMG and drag `4Charm.app` to `/Applications`
3. First launch — right-click the app → **Open** to bypass Gatekeeper on the ad-hoc signed build

---

## Usage

1. **Add URLs** — paste any 4chan thread, catalog, or board URL
2. **Start** — click Download and watch the live progress log
3. **Enjoy** — files are saved to your chosen download folder with automatic organization

---

## Disclaimer

4Charm is a media downloading helper for public 4chan threads and boards only. It is not affiliated with or endorsed by 4chan. You are solely responsible for complying with 4chan's rules, applicable copyright law, and the laws in your jurisdiction. The authors assume no liability for how you use this software.

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
# Workspace layout: sibling Apps/.razorcore provides editable razorcore
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

## Community & docs

- [BUILD_AND_RELEASE.md](BUILD_AND_RELEASE.md) — prerequisites, build, packaging, release, versioning
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to contribute
- [SECURITY.md](SECURITY.md) — vulnerability reporting
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — community standards

## License

MIT License — see [LICENSE](LICENSE) for details.
Copyright © 2026 RazorBackRoar

<!-- razorcore:runtime:start -->
## Runtime Requirements

For users:
- Download the macOS `.dmg` or `.app` release. Python does not need to be installed.

For developers:
- Primary development/build target: Python 3.14 with `uv`.
- Source/build target: Python 3.14 only.
- Setup: `uv sync`
- Run: `uv run python -m four_charm.main`
<!-- razorcore:runtime:end -->
