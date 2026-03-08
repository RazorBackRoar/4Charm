# 4Charm AGENTS

**Package:** `four_charm`
**Version:** 4.11.7

Use this file with `/Users/home/Workspace/Apps/AGENTS.md`. It only records 4Charm-specific context.

## Purpose And Entry Points

- Main app: `src/four_charm/main.py`
- Key areas: `src/four_charm/core/scraper.py`, `src/four_charm/gui/workers.py`, `src/four_charm/gui/main_window.py`
- Run locally: `uv run python -m four_charm.main`
- Build through workspace wrappers: `4charmbuild` or `razorbuild 4Charm`

## Non-Obvious Rules

- Use `razorcore.filesystem.sanitize_filename` for thread titles and downloaded media paths. Raw 4chan titles regularly contain macOS-hostile characters.
- Keep new 4chan fetch paths inside the app's rate-limited flow. Do not add request shortcuts that bypass throttling or retry behavior.
- Duplicate suppression relies on SHA-256 hashes tracked under a mutex. Do not replace that with filename-only checks or unsynchronized set access.
- New long-running GUI or download work should inherit `razorcore.threading.BaseWorker` so cancel/progress/error handling stays consistent.
- If a bundled app builds but fails on launch, inspect `4Charm.spec` first for asset/data and hidden-import drift before changing runtime code.

## Verification

Baseline:

```bash
uv run ruff check .
uv run ty check src --python-version 3.13
uv run pytest tests/ -q
```

Add focused checks when relevant:

- Scraper or download logic: run the closest tests in `tests/test_scraper_logic.py`, `tests/test_scraper_utils.py`, or `tests/test_workers.py`
- GUI or end-to-end download flow: run `uv run python -m four_charm.main`
- Shared-library behavior: make sure the editable `razorcore` source still points at `../.razorcore`

## CI Limitations

CI proves lint, type safety, and unit test correctness. It does NOT prove live-source scraper
reliability. Source site behavior changes cannot be caught by CI.

## Release Readiness Checklist

Before tagging a release, verify all of the following:
- [ ] `uv run ruff check .` passes with no errors
- [ ] `uv run ty check src --python-version 3.13` passes with no errors
- [ ] `uv run pytest tests/ -q` passes with no failures
- [ ] App launches locally from a clean `uv sync`
- [ ] At least one core user flow exercised manually end-to-end
- [ ] Packaging artifact built and smoke-tested (if applicable)
- [ ] `pyproject.toml` version matches README badge/display text

### What CI Does Not Prove
> Green CI is necessary but not sufficient for a safe release.
> Source site behavior (4Charm), macOS permissions (Nexus), and external tools (L!bra/Papyrus)
> cannot be fully validated by static CI checks.
