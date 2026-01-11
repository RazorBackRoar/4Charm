# WARP.md — 4Charm

> 4chan media downloader for macOS. Python 3.13+ / PySide6 / Apple Silicon.

## Quick Commands

```bash
# Run
python src/four_charm/main.py

# Test
pytest tests/

# Build
razorcore build 4Charm
```

## Architecture

| Component | Location | Purpose |
|-----------|----------|---------|
| **FourChanScraper** | `core/scraper.py` | HTTP scraping, rate limiting, SHA-256 dedup |
| **DownloadWorker** | `gui/workers.py` | Concurrent downloads with ThreadPoolExecutor |
| **MainWindow** | `gui/main_window.py` | URL input, progress tracking, live log |
| **config** | `config.py` | MAX_WORKERS, delays, user agent |

## Key Features
- Adaptive rate limiting with backoff
- SHA-256 duplicate detection
- Auto folder naming from board/thread/title
- Separate WEBM folder organization

## Config (config.py)
- `MAX_WORKERS`: Concurrent threads
- `BASE_DELAY` / `MAX_DELAY`: Rate limiting
- `MAX_RETRIES`: HTTP retries

## Rules
1. Build with `razorcore build 4Charm`
2. Version lives in `pyproject.toml`
3. Use QThread workers for downloads
4. Respect rate limits to prevent IP bans
