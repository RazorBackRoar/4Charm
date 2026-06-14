# 4Charm Four-Slot URL Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the default 4Charm window and present four visually double-spaced URL slots without changing URL parsing or queue behavior.

**Architecture:** Keep the existing composite `LineNumberTextEdit` and scrolling editor. Change the empty gutter floor from ten to four, increase both document block formats to 200% line height, and reduce only the window and editor dimensions.

**Tech Stack:** Python 3.14, PySide6, pytest, ruff, ty

**Repository constraint:** Do not commit, branch, push, or modify git history. Workspace autosync owns source-control mutations.

---

### Task 1: Lock The Four-Slot Contract

**Files:**
- Modify: `tests/test_gui.py`

- [ ] Change empty and four-URL gutter assertions to `1` through `4`.
- [ ] Assert a four-URL paste contains four document blocks and four queue entries.
- [ ] Assert the gutter and URL block formats use 200% proportional height.
- [ ] Assert the default size is 1280 by 820, minimum height is at most 780,
  and the URL frame is 120 pixels high.
- [ ] Run `uv run pytest tests/test_gui.py -q` and confirm failures describe the
  old ten-slot, 165% spacing, and large-window contract.

### Task 2: Implement The Compact Editor

**Files:**
- Modify: `src/four_charm/gui/widgets.py`
- Modify: `src/four_charm/gui/main_window.py`
- Modify: `src/four_charm/gui/style.qss`

- [ ] Set the initial and minimum gutter count to four.
- [ ] Set gutter and URL block line height to 200% proportional height.
- [ ] Set the window minimum to 1080 by 760 and default size to 1280 by 820.
- [ ] Set the URL editor frame to a fixed height of 120 pixels.
- [ ] Compact the stat cards, status bar, and outer vertical padding enough to
  prevent overlap at the default size without changing font or button height.
- [ ] Run `uv run pytest tests/test_gui.py -q` and confirm all focused tests pass.

### Task 3: Validate And Rebuild

**Files:**
- Modify: `4Charm.progress.md`
- Modify: `design-qa.md`

- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run ty check src --python-version 3.14`.
- [ ] Run `uv run pytest tests/ -q`.
- [ ] Render and inspect the source UI for four visible spaced rows and no
  overlap.
- [ ] Run `4charmbuild`.
- [ ] Verify the DMG checksum, signature, arm64 executable, bundled stylesheet,
  and packaged UI.
- [ ] Record the final QA result and update the progress tracker.
