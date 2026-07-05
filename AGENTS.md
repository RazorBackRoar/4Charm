# 4Charm AGENTS

**Package:** `four_charm`
**Version:** 2.0.0

Use this file with `../AGENTS.md`. It only records 4Charm-specific context.

## Purpose And Entry Points

- Main app: `src/four_charm/main.py`
- Key areas: `src/four_charm/core/scraper.py`, `src/four_charm/gui/workers.py`, `src/four_charm/gui/main_window.py`
- Run locally: `uv run python -m four_charm.main`
- Build through workspace wrappers: `4charmbuild` or `razorbuild 4Charm`

## Non-Obvious Rules

- 4Charm currently uses local reimplementations for logging, config, threading, and filesystem operations — it does not import razorcore. See `../Docs/razorcore-helper-audit.md` for the full audit.
- Keep new 4chan fetch paths inside the app's rate-limited flow. Do not add request shortcuts that bypass throttling or retry behavior.
- Duplicate suppression relies on SHA-256 hashes tracked under a mutex. Do not replace that with filename-only checks or unsynchronized set access.
- If a bundled app builds but fails on launch, inspect `4Charm.spec` first for asset/data and hidden-import drift before changing runtime code.

## Verification

Baseline:

```bash
uv run ruff check .
uv run ty check src --python-version 3.14
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
- [ ] `uv run ty check src --python-version 3.14` passes with no errors
- [ ] `uv run pytest tests/ -q` passes with no failures
- [ ] App launches locally from a clean `uv sync`
- [ ] At least one core user flow exercised manually end-to-end
- [ ] Packaging artifact built and smoke-tested (if applicable)
- [ ] `pyproject.toml` version matches README badge/display text

### What CI Does Not Prove
> Green CI is necessary but not sufficient for a safe release.
> Source site behavior (4Charm), macOS permissions (Nexus), and external tools (L!bra)
> cannot be fully validated by static CI checks.

## Universal Safety Rules

Before making changes, read and follow:

../../docs/Agent Pre-Safety Rules.md

---

## App Repository Rules

This is an individual app repository. Keep all changes scoped to this app
unless explicitly requested.
- Do not modify unrelated apps.
- Do not create branches unless explicitly requested.
- Do not switch branches unless explicitly requested.
- Do not create or switch worktrees unless explicitly requested.
- Do not commit unless explicitly requested.
- Do not push unless explicitly requested.
- Do not delete, rename, move, or overwrite unrelated files.
- Preserve existing project style and conventions.
- Keep changes minimal and targeted.

---

## App Environment

Assume:
- Apple Silicon macOS
- Python 3.14
- uv
- ruff
- ty
- pytest

Prefer:
    uv sync
    uv run ruff check .
    uv run ty check .
    uv run pytest

---

## App Workflow

Before editing:

1. Inspect relevant files.
2. Identify existing project commands.
3. Make the smallest safe change.
4. Avoid broad refactors unless explicitly requested.
5. Avoid dependency/config changes unless required.

---

## App Validation

After code changes, suggest or run relevant checks:
    uv run ruff check .
    uv run ty check .
    uv run pytest

If packaging/build files changed, inspect existing build scripts before
suggesting build commands. Do not claim validation passed unless actual command
output confirms it.

---

## 4Charm Notes

4Charm is a 4chan downloader app.
Preserve existing download, parsing, naming, and packaging behavior unless
explicitly requested.
Be careful with network/download logic:
- Do not broaden download scope without explicit approval.
- Do not change default output locations unless requested.
- Prefer dry-run or preview behavior for cleanup operations.


## Behavioral Guidelines

Shared behavioral guidelines (Think Before Coding, Simplicity First, Surgical
Changes, Goal-Driven Execution) are inherited from `../AGENTS.md` and the
workspace root `../../AGENTS.md`. Do not duplicate them here. Future changes
belong in the root AGENTS.md only, unless 4Charm needs a specific local
exception.
