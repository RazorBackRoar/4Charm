# Claude Code — 4Charm

See workspace policy: `/Users/home/Workspace/CLAUDE.md`

## Context load order
1. `/Users/home/Workspace/CLAUDE.md`
2. `/Users/home/Workspace/Apps/AGENTS.md`
3. `/Users/home/Workspace/Apps/4Charm/AGENTS.md` ← nearest, wins on conflicts
4. Relevant `~/.skills/` guides

## Quick reference
- **Purpose:** High-performance native macOS 4chan media downloader
- Package: `four_charm` | Entry: `python -m four_charm.main`
- Launch: `./run_preview.sh`
- Build: `4charmbuild` or `razorbuild 4Charm` | Push: `4charmpush` or `razorpush 4Charm`
- Toolchain: `uv sync` → `uv run ruff check .` → `uv run ty check src --python-version 3.13`
- Tests: `uv run pytest tests/ -v`
- razorcore: editable dep at `../.razorcore`
- **⚠️ Always use `sanitize_filename()` from razorcore.filesystem** — 4chan thread titles contain `/`, `:`, `\0` that cause `OSError` on macOS without sanitization
- **⚠️ Rate limiting mandatory**: 1 req/s to 4chan API (`time.sleep(1)` between all requests); 429s require exponential backoff

## Module structure (post-refactor)
- `transport/session.py` — HTTP session factory (no Qt dependency); `create_session()` returns configured `requests.Session`
- `core/dedup.py` — thread-safe SHA-256 dedup via `threading.Lock` (not QMutex); `DedupTracker.check_and_register()` / `.add()`
- `core/scraper.py` — orchestrator only; imports from `transport.session` and `core.dedup`
