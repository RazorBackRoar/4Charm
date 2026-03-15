# WARP.md — 4Charm

> **⭐ CODEGRAPHCONTEXT:** [/Users/home/Workspace/Apps/.code-analysis/monorepo-analysis.md](file:///Users/home/Workspace/Apps/.code-analysis/monorepo-analysis.md)
> **⭐ QUERIES:** [/Users/home/Workspace/Apps/.code-analysis/essential-queries.md](file:///Users/home/Workspace/Apps/.code-analysis/essential-queries.md)
> **Agent Context:** [/Users/home/Workspace/Apps/4Charm/AGENTS.md](file:///Users/home/Workspace/Apps/4Charm/AGENTS.md)

## ⚡ Quick Commands

| Action | Command | Notes |
| --- | --- | --- |
| **Push** | `razorpush 4Charm` | Commit and save 4Charm only |
| **Build (Release)** | `4charmbuild` | Full .app + DMG (~3m) |
| **Verify** | `uv run pytest tests/ -q` | Fastest reliable repo-level check |
| **Run** | `uv run python -m four_charm.main` | Dev run |

## 🏗️ Architecture

| Component | Location | Purpose |
| --- | --- | --- |
| **FourChanScraper** | `src/four_charm/core/scraper.py` | HTTP scraping, resume logic, duplicate checks, adaptive delay |
| **MultiUrlDownloadWorker** | `src/four_charm/gui/workers.py` | `QObject` worker that coordinates thread-pool downloads |
| **MainWindow** | `src/four_charm/gui/main_window.py` | URL input, progress tracking, folder selection, worker thread lifecycle |
| **Config** | `src/four_charm/config.py` | Worker limits, delays, retries, user agent |

## 🔑 Key Features

- Adaptive rate limiting with backoff
- SHA-256 duplicate detection
- Auto folder naming from board/thread/title
- `Ctrl+Return` starts downloads from the URL editor

## 🚨 Rules

1. **Python Lock**: **STRICTLY 3.13.x**.
2. **Imports**: Absolute ONLY (`from four_charm.core import X`).
3. **Threading**: Current download flow uses `QObject` workers moved onto a `QThread`, with `ThreadPoolExecutor` for concurrent downloads. New long-running GUI/download work should follow repo `AGENTS.md` guidance and prefer `razorcore.threading.BaseWorker` when practical.
4. **Version**: Read from `pyproject.toml` (SSOT).
