# WARP.md — 4Charm

> **⭐ CODEGRAPHCONTEXT:** [/Users/home/Workspace/Apps/.code-analysis/monorepo-analysis.md](file:///Users/home/Workspace/Apps/.code-analysis/monorepo-analysis.md)
> **⭐ QUERIES:** [/Users/home/Workspace/Apps/.code-analysis/essential-queries.md](file:///Users/home/Workspace/Apps/.code-analysis/essential-queries.md)
> **Agent Context:** [/Users/home/Workspace/Apps/4Charm/AGENTS.md](file:///Users/home/Workspace/Apps/4Charm/AGENTS.md)

## ⚡ Quick Commands

| Action | Command | Notes |
| --- | --- | --- |
| **Push** | `razorpush 4Charm` | Commit and save 4Charm only |
| **Build (Release)** | `4charmbuild` | Full .app + DMG (~3m) |
| **Build (Test)** | `4charmtest` | Fast .app only (~45s) |
| **Run** | `python src/four_charm/main.py` | Dev run |

## 🏗️ Architecture

| Component | Location | Purpose |
| --- | --- | --- |
| **FourChanScraper** | `core/scraper.py` | HTTP scraping, rate limiting, SHA-256 dedup |
| **DownloadWorker** | `gui/workers.py` | Concurrent downloads with ThreadPoolExecutor (Must inherit BaseWorker) |
| **MainWindow** | `gui/main_window.py` | URL input, progress tracking, live log (Must inherit SpaceBarAboutMixin) |
| **config** | `config.py` | MAX_WORKERS, delays, user agent |

## 🔑 Key Features

- Adaptive rate limiting with backoff
- SHA-256 duplicate detection
- Auto folder naming from board/thread/title

## 🚨 Rules

1. **Python Lock**: **STRICTLY 3.13.x**.
2. **Imports**: Absolute ONLY (`from four_charm.core import X`).
3. **Threading**: Use `BaseWorker` (never raw QThread).
4. **Version**: Read from `pyproject.toml` (SSOT).
