# 4Charm AGENTS

**Package:** `four-charm` (import: `four_charm`)
**Version:** 2.0.1
**GitHub:** `RazorBackRoar/4Charm`

Use with `../AGENTS.md`. Keep this file 4Charm-specific.

## Purpose and entry points

Native macOS 4chan media downloader (PySide6).

- Main: `src/four_charm/main.py`
- Core: `src/four_charm/core/scraper.py` (orchestrator)
- Transport: `src/four_charm/transport/api.py` (`BoardApi` protocol + `LiveBoardApi`)
- Workers: `src/four_charm/gui/workers.py` (`QObject` + `ThreadPoolExecutor`)
- UI: `src/four_charm/gui/main_window.py`
- Run: `uv run python -m four_charm.main`
- Build: `4charmbuild` or `razorbuild 4Charm`

Dev clones expect sibling `../.razorcore` (editable `razorcore>=1.211.0`).

## Core architecture (scraper seams)

Recent refactors split the scraper into injectable seams. ADRs in `docs/adr/` are the
design record; this section is the agent quick-reference.

| Module | Role |
|--------|------|
| `transport/api.py` | `BoardApi` protocol (`fetch_thread`, `fetch_catalog`, `stream_range`) + `LiveBoardApi`. Tests inject `FakeBoardApi` instead of monkeypatching `safe_get`. See ADR-0001. |
| `core/retry.py` | `RetryPolicy` — exponential backoff + adaptive rate-limit delay (stateful per scraper). |
| `core/chunking.py` | `ChunkSelector` — adaptive streaming chunk sizes from `config.ADAPTIVE_CHUNK_THRESHOLDS`. |
| `core/paths.py` | `PathBuilder` — download path construction, folder sanitization, containment checks. Public `sanitize_filename` delegates to razorcore with `MAX_FILENAME_LENGTH`. |
| `core/error_format.py` | `ErrorFormatter` — classifies `requests` exceptions for retry/UI messaging. |
| `core/signals.py` | `DownloadTask` dataclass carried on the worker `progress` signal (replaces 7-arg tuple). See ADR-0002. |

Invariant: 4chan fetch paths stay inside the rate-limited flow. Any new `BoardApi` adapter
must honour `RetryPolicy.adaptive_delay` (or document why not).

## CI: vendored razorcore wheel

GitHub Actions installs razorcore from `ci/vendor/` (not the private repo).
After changing `.razorcore`, run `razorvendor` from the Apps workspace root.
See `ci/vendor/README.md`.

## razorcore integration (v1.1)

| Surface | Usage |
| --- | --- |
| `logging` | Size-based rotation (`max_bytes=5MB`, `configure_root=True`) via `four_charm/utils/logging_setup.py` |
| `config.get_version` | Version resolution (`package_name="four-charm"`) |
| `appinfo` / `updates` | Startup banner, About (`package_name=PACKAGE_NAME`) |
| `filesystem.sanitize_filename` | Via `_rc_sanitize_filename` with `max_length=config.MAX_FILENAME_LENGTH` |
| `threading.BaseWorker` | **Not used** — workers stay on `QObject` + pool with 7-arg progress/ETA and scraper cancel |

User settings JSON remains in local `config.py`.

## Non-obvious rules

- Keep 4chan fetch paths inside the rate-limited flow; do not bypass throttling or retries.
- Duplicate suppression uses SHA-256 under a mutex — not filename-only checks.
- If a bundled app builds but fails to launch, inspect `4Charm.spec` for asset/hidden-import drift before changing runtime code.
- Do not broaden download scope or change default output locations without explicit approval.

## Verification

```bash
uv run ruff check .
uv run ty check src --python-version 3.14
uv run pytest tests/ -q
```

Focused: `tests/test_scraper_logic.py`, `tests/test_scraper_utils.py`, `tests/test_workers.py`. GUI smoke: `uv run python -m four_charm.main`.

## CI limitations

CI covers lint, types, and unit tests. It does **not** prove live 4chan source behavior.

## Release checklist

- [ ] ruff / ty / pytest clean
- [ ] App launches after clean `uv sync`
- [ ] One end-to-end download flow exercised
- [ ] Packaging artifact smoke-tested when shipping a DMG
- [ ] `pyproject.toml` version matches README badge

## Safety and scope

- Read `../../docs/Agent Pre-Safety Rules.md` before changes.
- Keep changes scoped to this app unless asked otherwise.
- Do not create branches, commit, or push unless explicitly requested.
- Behavioral guidelines inherit from `../AGENTS.md`.
