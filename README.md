# 4Charm

> Workspace context source: `/Users/home/Workspace/Apps/.code-analysis/` (`AGENTS.md`, `monorepo-analysis.md`, `essential-queries.md`).

[![CI](https://github.com/RazorBackRoar/4Charm/actions/workflows/ci.yml/badge.svg)](https://github.com/RazorBackRoar/4Charm/actions/workflows/ci.yml)
[![Ruff](https://github.com/RazorBackRoar/4Charm/actions/workflows/ruff.yml/badge.svg)](https://github.com/RazorBackRoar/4Charm/actions/workflows/ruff.yml)
[![Version](https://img.shields.io/badge/version-4.11.7-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Apple
Silicon](https://img.shields.io/badge/Apple%20Silicon-Native-brightgreen.svg)](https://support.apple.com/en-us/HT211814)
[![PySide6](https://img.shields.io/badge/PySide6-Qt6-orange.svg)](https://doc.qt.io/qtforpython/)

```text
██╗  ██╗ ██████╗██╗  ██╗ █████╗ ██████╗ ███╗   ███╗
██║  ██║██╔════╝██║  ██║██╔══██╗██╔══██╗████╗ ████║
███████║██║     ███████║███████║██████╔╝██╔████╔██║
╚════██║██║     ██╔══██║██╔══██║██╔══██╗██║╚██╔╝██║
██║╚██████╗██║  ██║██║  ██║██║  ██║██║ ╚═╝ ██║
╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
```

> **High-performance native macOS 4chan media downloader**
> Download entire threads, catalogs, or boards with intelligent organization,
fail-safe resume, and zero duplicates.

---

## ✨ Features

- 🚀 **Performance** – Native macOS app built with PySide6 (Qt6)
- 🧵 **Bulk Downloading** – Queue up to 20 threads/catalogs simultaneously
- 📂 **Smart Organization** – Automatic folder structure with WEBM separation
- 🔄 **Fail-Safe Resume** – Automatically resumes interrupted downloads
- 🔍 **Duplicate Prevention** – SHA-256 hashing prevents redownloading files
- 🛡️ **Rate Limiting** – Adaptive throttling prevents IP bans
- 🖥️ **Apple Silicon Native** – Optimized for M1/M2/M3 chips

---

## 🚀 Quick Start

### Installation

1. Download the latest `4Charm.dmg` from

   [Releases](https://github.com/RazorBackRoar/4Charm/releases)

2. Drag `4Charm.app` to `/Applications`
3. **First Launch**:

```bash
   # If prompted with "App is damaged":
   sudo xattr -cr /Applications/4Charm.app
```

### Usage

1. **Launch App**: Open 4Charm from Applications
2. **Add URLs**: Paste 4chan thread or catalog URLs
3. **Download**: Click "Start Download" and watch the live log
4. **Enjoy**: Files are saved to your chosen download location

---

## 🛠️ Development

This project uses `.razorcore` for build tooling.

### Prerequisites

- Python 3.13
- macOS 10.13+

### Setup

```bash
git clone https://github.com/RazorBackRoar/4Charm.git
cd 4Charm
uv venv --python 3.13
uv sync
uv add --editable ../.razorcore
```

### Build & Release

```bash
## Build app and create DMG
razorbuild 4Charm

## Create release (auto-commits & tags)
razorcore save 4Charm
```

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.
Copyright © 2026 RazorBackRoar
