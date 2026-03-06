# 🍀 4Charm - 4chan Media Downloader Agent

> Level 2 Document: Refer to /Users/home/Workspace/Apps/AGENTS.md (Level 1) for global SSOT standards.

**Package:** `four_charm`
**Version:** 4.11.2
**Context Level:** LEVEL 3 (Application-Specific)

---

## 🏁 GLOBAL AUTHORITY

All standard patterns must follow:
👉 **`/Users/home/Workspace/Apps/CONTEXT.md`**
👉 **`/Users/home/Workspace/Apps/.code-analysis/monorepo-analysis.md`**
👉 **`/Users/home/Workspace/Apps/.code-analysis/essential-queries.md`**
👉 **`/Users/home/Workspace/Apps/.code-analysis/AGENTS.md`**

This file contains **4Charm-specific** overrides and critical implementation details.

When opening this project/workspace, load context in this order:

1. `/Users/home/Workspace/Apps/CONTEXT.md`
2. `/Users/home/Workspace/Apps/.code-analysis/monorepo-analysis.md`
3. `/Users/home/Workspace/Apps/.code-analysis/essential-queries.md`
4. `/Users/home/Workspace/Apps/.code-analysis/AGENTS.md`

---

## 🎯 Quick Context

- **Purpose:** High-performance native macOS 4chan media downloader
- **Primary Tech:** PySide6, requests, razorcore
- **Key Modules:** `scraper.py`, `downloader.py`, `workers.py`
- **Build Commands:** `4charmbuild` or `razorbuild 4Charm`

---

## ⚡ Critical 4Charm-Specific Rules

### ⚡ Performance Optimization (Bolt)

- **Agent:** Bolt ⚡
- **Activation:** `bolt` (alias `snake`) or `razorcore bolt`
- **Goal:** < 2s startup, < 50MB bundle
- **Journal:** `.razorcore/bolt/journal.md`

### 1. File Naming (MANDATORY - Will Crash Without This)

```python
# ✅ ALWAYS use razorcore's sanitizer for ALL file operations
from razorcore.filesystem import sanitize_filename

# 4chan thread titles contain macOS-reserved characters: / : \0
thread_title = "Linux/Unix: tips & tricks"
safe_name = sanitize_filename(thread_title)  # → "Linux_Unix_ tips & tricks"

# Use for all downloads
file_path = download_dir / safe_name / image_filename
```

**Why:** 4chan thread titles frequently contain `/`, `:`, `\0` that cause `OSError` on macOS.

### 2. 4chan API Rate Limiting (Required)

```python
import time
from requests.exceptions import HTTPError


class FourChanScraper:
    """All API interactions MUST implement rate limiting."""

    RATE_LIMIT_DELAY = 1.0  # Minimum 1 second between requests

    def fetch_thread(self, board: str, thread_id: int):
        try:
            response = requests.get(
                f"https://a.4cdn.org/{board}/thread/{thread_id}.json",
                timeout=10,
            )
            response.raise_for_status()

            # ⚠️ MANDATORY: Wait before next request
            time.sleep(self.RATE_LIMIT_DELAY)

            return response.json()
        except HTTPError as e:
            if e.response.status_code == 429:  # Too Many Requests
                # Exponential backoff: 2, 4, 8, 16 seconds
                wait_time = 2 ** self._retry_count
                time.sleep(wait_time)
```

**Limits:**

- **Global:** 1 request/second to 4chan API
- **Thread Fetching:** Use CDN URLs (`<<<<<<<<https://a.4cdn.org/>>>>>>>>`)
- **Media Downloads:** Use media CDN (`<<<<<<<<https://i.4cdn.org/>>>>>>>>`)

### 3. Download Queue Architecture (BaseWorker Required)

```python
from razorcore.threading import BaseWorker  # MANDATORY inheritance
from PySide6.QtCore import Signal


class DownloadWorker(BaseWorker):
    """
    All long-running downloads MUST inherit from BaseWorker.
    This ensures thread safety and proper GUI responsiveness.
    """
    # BaseWorker provides: progress, finished, error signals

    def __init__(self, thread_url: str, output_dir: str):
        super().__init__()
        self.thread_url = thread_url
        self.output_dir = output_dir

    def run(self):
        """Main download logic runs in separate thread."""
        try:
            self.progress.emit(0, "Fetching thread metadata...")

            thread_data = self.scraper.fetch_thread(board, thread_id)

            total_files = len(thread_data['posts'])
            for i, post in enumerate(thread_data['posts']):
                if self.is_canceled():  # Check for user cancellation
                    return

                self._download_file(post)

                progress_pct = int((i + 1) / total_files * 100)
                self.progress.emit(progress_pct, f"Downloaded {i+1}/{total_files}")

            self.finished.emit()
        except Exception as e:
            self.error.emit(f"Download failed: {str(e)}")
```

### 4. Duplicate Detection (SHA-256 Hashing)

```python
from razorcore.filesystem import compute_file_hash
import sqlite3


class DuplicateChecker:
    """Prevents re-downloading the same media files."""

    def __init__(self, db_path: str = "~/.4charm/hashes.db"):
        self.db_path = Path(db_path).expanduser()
        self._init_database()

    def is_duplicate(self, file_path: Path) -> bool:
        """Check if file hash already exists in database."""
        file_hash = compute_file_hash(file_path)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM files WHERE hash = ?",
                (file_hash,),
            )
            return cursor.fetchone()[0] > 0

    def mark_downloaded(self, file_path: Path):
        """Store file hash to prevent future duplicates."""
        file_hash = compute_file_hash(file_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO files (hash, path) VALUES (?, ?)",
                (file_hash, str(file_path)),
            )
```

---

## 🏗️ 4Charm Project Structure

```text
4Charm/
├── src/four_charm/
│   ├── __init__.py              # Contains __version__
│   ├── main.py                  # Entry point (calls print_startup_info)
│   ├── core/
│   │   ├── scraper.py           # 4chan API interaction (rate limiting here)
│   │   ├── downloader.py        # File download + SHA-256 hashing
│   │   └── validators.py        # URL validation for 4chan threads
│   ├── gui/
│   │   ├── main_window.py       # Main UI (inherits SpaceBarAboutMixin)
│   │   └── workers.py           # QThread workers (all inherit BaseWorker)
│   └── utils/
│       └── config.py            # User settings management
├── assets/
│   └── icons/4Charm.icns        # Application icon (REQUIRED)
├── tests/
│   ├── test_scraper.py          # API interaction tests
│   └── test_downloader.py       # Download logic tests
├── 4Charm.spec                  # PyInstaller config (hiddenimports!)
├── pyproject.toml               # Version SSOT
└── AGENTS.md                    # This file
```

---

## 🔧 Build & Deploy Commands

```bash
# Full release build (app + DMG + Git tag, ~3min)
4charmbuild

# Canonical build entry
razorbuild 4Charm

# Push changes (auto-commit, auto-version, auto-tag)
razorpush 4Charm

# Run tests
uv run pytest tests/

# Check compliance
razorcheck
```

---

## ✅ Required Workflows

- Run `razorcheck` before committing or opening a PR.
- Use `razorpush 4Charm` (or `4charmpush`) for commit, version bump, tag, and push. Do not edit versions manually.
- Build via `4charmbuild` or `razorbuild 4Charm`. **Never** run `universal-build.sh` directly.
- Use `razoragents` to sync `AGENTS.md` tables (usually run by `razorpush`).
- If you change `.razorcore` CLI commands or `pyproject.toml`, run `uv add --editable ../.razorcore`.
- **Always run the app after making changes** (`uv run python -m four_charm.main`) to visually verify updates before considering any task complete. This is mandatory—do not skip this step.

---

## 🚨 Common Pitfalls & Solutions

### ❌ Error: "OSError: Invalid argument" when saving files

**Cause:** Using raw 4chan thread titles as filenames (contain `/`, `:`)
**Fix:**

```python
from razorcore.filesystem import sanitize_filename
safe_name = sanitize_filename(thread_title)  # ALWAYS use this
```

### ❌ Error: "HTTPError 429: Too Many Requests"

**Cause:** Not implementing rate limiting for 4chan API
**Fix:** Add `time.sleep(1)` between ALL requests to 4chan

### ❌ Error: "ModuleNotFoundError: No module named 'razorcore'"

**Cause:** Shared library not installed in editable mode
**Fix:**

```bash
cd /Users/home/Workspace/Apps/4Charm
uv add --editable ../.razorcore
```

### ❌ Downloads Complete but App Freezes

**Cause:** Running downloads in main thread instead of QThread
**Fix:** Ensure all `DownloadWorker` classes inherit from `BaseWorker`

### ❌ Build Succeeds but .app Crashes on Launch

**Cause:** Missing `hiddenimports` in `4Charm.spec`
**Fix:** Add to spec file:

```python
hiddenimports=[
    'razorcore.styling',
    'razorcore.threading',
    'razorcore.appinfo',
    'razorcore.filesystem',
]
```

---

## 🧪 Testing Strategy

```bash
# Run all tests
uv run pytest tests/

# Test with coverage (must meet 80%+ for core modules)
uv run pytest --cov=src/four_charm --cov-report=html tests/

# Test specific module
uv run pytest tests/test_scraper.py -v

# Test API rate limiting (slow test)
uv run pytest tests/test_scraper.py::test_rate_limiting -v
```

---

## 📚 Related Documentation

- **CodeGraphContext Docs:** `/Users/home/Workspace/Apps/.code-analysis/monorepo-analysis.md`
- **CodeGraphContext Queries:** `/Users/home/Workspace/Apps/.code-analysis/essential-queries.md`
- **Code Analysis Agent Rules:** `/Users/home/Workspace/Apps/.code-analysis/AGENTS.md`
- **CLI Commands:** `/Users/home/Workspace/Apps/Docs/cli_commands.md`
- **CLI Inventory (Full):** `/Users/home/Workspace/Apps/Docs/cli_inventory.md`
- **4Charm Manual:** `/Users/home/Workspace/Apps/Docs/4charm_manual.md`
- **Engineering Hub:** `/Users/home/Workspace/Apps/AGENTS.md` (LEVEL 2)

---

## 🎯 When to Use What

| Scenario | Command/Pattern |
| --- | --- |
| Run app locally | `uv run python -m four_charm.main` |
| Quick .app build for testing | `razorbuild 4Charm` |
| Release to production | `4charmbuild` |
| Save work with version bump | `razorpush 4Charm` |
| Add new API endpoint | Check `scraper.py`, add rate limiting |
| Process thread titles | **ALWAYS** use `sanitize_filename()` |
| Long-running operation | Inherit from `BaseWorker` |
| Check for duplicates | Use SHA-256 hash lookup before download |

---

## RazorCore Usage

See `/Users/home/Workspace/Apps/.razorcore/AGENTS.md` for the complete public API and safety rules.

---

## 🚀 Power-User Architecture & Quality Tools

This project follows the RazorBackRoar workspace power-user architecture for multi-agent coordination and standardized quality assurance.

### 📋 Multi-Agent Execution Protocol

**Control Plane:** AGENTS.md files serve as enforceable execution policies

**Branch Isolation:** One task per branch with naming conventions:

- `feat/task-name` - New features
- `fix/issue-description` - Bug fixes
- `refactor/component-name` - Code improvements

**Task Contract:** Standard task structure includes:

- Objective, scope, constraints, commands, deliverables
- Evidence bundle with diffs, test outputs, benchmarks
- Demo-like runbook for reproducible execution

### 🛠️ Standardized Quality Scripts

Load the master quality script for complete code quality workflow:

```bash
# Load all quality functions (run once per session)
source ~/.skills/scripts/quality.sh

# Quick development check
quality_quick

# Full check with auto-fixes and coverage
quality_full

# Strict pre-commit validation
quality_precommit

# Check specific file
quality_file src/four_charm/main.py
```

**Available Scripts:**

- `~/.skills/scripts/quality.sh` - Master script (test + lint + format)
- `~/.skills/scripts/test.sh` - Pytest execution with coverage
- `~/.skills/scripts/lint.sh` - Ruff linting + ty type checking
- `~/.skills/scripts/format.sh` - Ruff code formatting

**Quick Reference:**

```bash
# Individual operations
source ~/.skills/scripts/test.sh && test_quick
source ~/.skills/scripts/lint.sh && check_quick
source ~/.skills/scripts/format.sh && format_all

# Project setup with quality tools
source ~/.skills/scripts/quality.sh && setup_quality
```

### 📚 Documentation

- **Power-User Protocol:** `~/.skills/agents.md`
- **Quality Scripts:** `~/.skills/scripts/README.md`
- **Workspace Standards:** `/Users/home/Workspace/Apps/AGENTS.md`

<!-- verification check Thu Feb 26 04:26:00 MST 2026 -->
