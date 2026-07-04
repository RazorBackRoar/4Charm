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

- Use `razorcore.filesystem.sanitize_filename` for thread titles and downloaded media paths. Raw 4chan titles regularly contain macOS-hostile characters.
- Keep new 4chan fetch paths inside the app's rate-limited flow. Do not add request shortcuts that bypass throttling or retry behavior.
- Duplicate suppression relies on SHA-256 hashes tracked under a mutex. Do not replace that with filename-only checks or unsynchronized set access.
- New long-running GUI or download work should inherit `razorcore.threading.BaseWorker` so cancel/progress/error handling stays consistent.
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

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use your judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
