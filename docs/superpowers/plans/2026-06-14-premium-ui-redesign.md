# 4Charm Premium UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved Layout A interface with a wide activity log, right-side stats rail, premium black/white/green styling, and unchanged downloader behavior.

**Architecture:** Keep the existing PySide6 widgets, signals, workers, URL editor, and statistics APIs. Change only widget composition, display labels, and QSS presentation, with focused tests for the stable UI contract.

**Tech Stack:** Python 3.14, PySide6, Qt Style Sheets, pytest, ruff, ty

**Repository constraint:** Do not commit, branch, push, or modify git history. Workspace autosync owns source-control mutations.

---

### Task 1: Lock The UI Contract With Focused Tests

**Files:**
- Modify: `tests/test_gui.py`

- [ ] **Step 1: Add a test for the approved idle-state labels and initial values**

Append:

```python
def test_premium_idle_ui_contract() -> None:
    """The idle UI should expose polished labels and the approved initial stats."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from four_charm.gui.main_window import MainWindow

    app = _app()
    window = MainWindow()

    try:
        assert window.start_cancel_btn.text() == "Start Download"
        assert window.clear_btn.text() == "Clear"
        assert window.folder_btn.text() == "Folder"
        assert window.pause_resume_btn.text() == "Pause"
        assert window.progress_label.text() == "Ready"
        assert window.folders_card.value_label.text() == "0"
        assert window.files_card.value_label.text() == "0"
        assert window.storage_card.value_label.text() == "0.0GB"
        assert window.status_bar.currentMessage() == "Engine Status: Ready"
    finally:
        window.deleteLater()
        app.processEvents()
```

- [ ] **Step 2: Add a test for the Layout A lower-area composition**

Append:

```python
def test_lower_area_places_stats_to_the_right_of_log() -> None:
    """Layout A should use a wide log with a vertical stats rail."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

    from four_charm.gui.main_window import MainWindow

    app = _app()
    window = MainWindow()

    try:
        assert isinstance(window.lower_layout, QHBoxLayout)
        assert isinstance(window.stats_layout, QVBoxLayout)
        assert window.lower_layout.indexOf(window.log_panel) == 0
        assert window.lower_layout.indexOf(window.stats_panel) == 1
        assert window.stats_layout.indexOf(window.folders_card) == 0
        assert window.stats_layout.indexOf(window.files_card) == 1
        assert window.stats_layout.indexOf(window.storage_card) == 2
    finally:
        window.deleteLater()
        app.processEvents()
```

- [ ] **Step 3: Run the focused tests and confirm the new contract fails**

Run:

```bash
uv run pytest tests/test_gui.py -q
```

Expected: existing tests pass and the two new tests fail because the old labels,
progress text, and horizontal stat row are still present.

### Task 2: Implement Layout A And Polished State Labels

**Files:**
- Modify: `src/four_charm/gui/main_window.py:140-325`
- Modify: `src/four_charm/gui/main_window.py:559-636`

- [ ] **Step 1: Remove glow usage and target the approved desktop size**

Remove `apply_neon_glow` from the widget imports. Set:

```python
self.setMinimumSize(980, 720)
self.resize(1100, 760)
```

Use main margins `24, 16, 24, 14` and spacing `12`.

- [ ] **Step 2: Build the approved hierarchy**

In `_build_ui`, retain header, URL panel, progress panel, and status bar. Replace
the separate lower-area and stat-row additions with:

```python
lower_area = self._build_lower_area()

main_layout.addWidget(header)
main_layout.addWidget(url_panel)
main_layout.addWidget(progress_panel)
main_layout.addWidget(lower_area, stretch=1)
```

Remove the redundant marketing footer so the native status bar is the only
bottom bar.

- [ ] **Step 3: Tighten the header and URL panel**

Use compact header margins and no graphics effect:

```python
layout.setContentsMargins(0, 8, 0, 10)
layout.setSpacing(4)
```

Set the URL editor minimum height:

```python
self.url_input_frame.setMinimumHeight(190)
```

Use emoji-free controls:

```python
self.start_cancel_btn = NeonButton("Start Download")
self.clear_btn = NeonButton("Clear")
self.folder_btn = NeonButton("Folder")
self.pause_resume_btn = NeonButton("Pause")
```

Keep the pause button transient and preserve all current signal connections.

- [ ] **Step 4: Compose the lower area as log plus vertical stats rail**

Store the layout and panels for stable test access:

```python
wrapper = QWidget()
self.lower_layout = QHBoxLayout(wrapper)
self.lower_layout.setContentsMargins(0, 0, 0, 0)
self.lower_layout.setSpacing(12)

self.log_panel = NeonPanel("LogPanel")
log_layout = QVBoxLayout(self.log_panel)
log_layout.setContentsMargins(14, 12, 14, 14)
log_layout.setSpacing(8)

self.stats_panel = QWidget()
self.stats_panel.setObjectName("StatsPanel")
self.stats_panel.setFixedWidth(240)
self.stats_layout = QVBoxLayout(self.stats_panel)
self.stats_layout.setContentsMargins(0, 0, 0, 0)
self.stats_layout.setSpacing(10)

self.folders_card = StatCard("Folders", "0", "F")
self.files_card = StatCard("Files", "0", "D")
self.storage_card = StatCard("Storage", "0.0GB", "S")

self.stats_layout.addWidget(self.folders_card)
self.stats_layout.addWidget(self.files_card)
self.stats_layout.addWidget(self.storage_card)
self.stats_layout.addStretch()
self.lower_layout.addWidget(self.log_panel, stretch=1)
self.lower_layout.addWidget(self.stats_panel)
```

The letter marks are styled monochrome identifiers, not emoji.

- [ ] **Step 5: Use concise user-facing state labels without altering state logic**

Set the idle progress text to `Ready`. Update button state text to:

```python
if state == "idle":
    self.start_cancel_btn.setText("Start Download")
    self.pause_resume_btn.setText("Pause")
elif state == "downloading":
    self.start_cancel_btn.setText("Cancel")
    self.pause_resume_btn.setText("Pause")
elif state == "paused":
    self.pause_resume_btn.setText("Resume")
```

Keep the existing object-name changes, visibility changes, enablement, worker
calls, and statistics updates.

In `update_progress`, calculate `percent = int((current / total) * 100)` once,
set the bar to that value, and lead the detailed message with
`Downloading {percent}%`.

- [ ] **Step 6: Run focused tests**

Run:

```bash
uv run pytest tests/test_gui.py -q
```

Expected: all GUI tests pass.

### Task 3: Replace Neon Widget Presentation With Premium Components

**Files:**
- Modify: `src/four_charm/gui/widgets.py:5-71`

- [ ] **Step 1: Remove the drop-shadow implementation**

Remove `QColor`, `QGraphicsDropShadowEffect`, and `apply_neon_glow`. Keep the
existing class names to avoid unnecessary import churn:

```python
class NeonPanel(QFrame):
    def __init__(self, object_name: str = "NeonPanel") -> None:
        super().__init__()
        self.setObjectName(object_name)


class NeonButton(QPushButton):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setMinimumHeight(46)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
```

- [ ] **Step 2: Make stat cards vertical-rail friendly**

Use a 68-pixel minimum height, a 28-pixel monochrome mark, and a readable label:

```python
self.setMinimumHeight(68)

icon_label = QLabel(icon)
icon_label.setObjectName("StatIcon")
icon_label.setFixedSize(28, 28)
icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

title = QLabel(label)
title.setObjectName("StatLabel")

layout = QHBoxLayout(self)
layout.setContentsMargins(12, 10, 12, 10)
layout.setSpacing(10)
```

Keep `value_label` and `set_value` unchanged so counting behavior is untouched.

- [ ] **Step 3: Run focused lint and tests**

Run:

```bash
uv run ruff check src/four_charm/gui/widgets.py src/four_charm/gui/main_window.py tests/test_gui.py
uv run pytest tests/test_gui.py -q
```

Expected: both commands pass.

### Task 4: Apply The Premium Black, White, And Green Visual System

**Files:**
- Modify: `src/four_charm/gui/style.qss`

- [ ] **Step 1: Replace the global palette and top/bottom rules**

Use:

```css
QWidget {
    color: #f3f6f4;
    font-family: "SF Pro Text", "-apple-system", "Helvetica Neue", sans-serif;
    font-size: 13px;
}

QMainWindow,
#Root {
    background: #080b09;
}

#Root {
    border-top: 2px solid #55df72;
}
```

- [ ] **Step 2: Style the hierarchy and neutral surfaces**

Use green only for accents. Apply charcoal backgrounds, `#2a312d` borders,
10-pixel radii, white section labels, and a 3-pixel green left border on
section labels. Style the title at 42 pixels, weight 700, with no glow.

- [ ] **Step 3: Style URL input, buttons, progress, log, and stats**

Use:

```css
#UrlInputFrame {
    background: #070908;
    border: 1px solid #31513a;
    border-radius: 9px;
}

#UrlEditor {
    color: #f4f6f5;
}

QPushButton {
    background: #151a17;
    color: #f4f6f5;
    border: 1px solid #39413c;
    border-radius: 8px;
}

#startBtn {
    background: #17351f;
    border-color: #58df73;
}

#DownloadProgress {
    background: #252b27;
    border: 1px solid #303733;
}

#DownloadProgress::chunk {
    background: #55df72;
}

#ActivityLog {
    background: #070908;
    color: #d8ddda;
    border: 1px solid #29302c;
}

#StatCard {
    background: #121613;
    border: 1px solid #2b332e;
    border-radius: 10px;
}

#StatValue {
    color: #62e17a;
    background: #0b120d;
    border: 1px solid #3d7449;
    border-radius: 10px;
}
```

Add clear hover, pressed, disabled, scrollbar, and status-bar states. The status
bar uses a green top border and light text.

- [ ] **Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/test_gui.py -q
```

Expected: all GUI tests pass.

### Task 5: Full Validation And Visual Inspection

**Files:**
- Modify: `4Charm.progress.md`

- [ ] **Step 1: Run the repository validation baseline**

Run:

```bash
uv run ruff check .
uv run ty check src --python-version 3.14
uv run pytest tests/ -q
```

Expected: all commands pass.

- [ ] **Step 2: Launch the app and inspect the rendered interface**

Run:

```bash
./run_preview.sh
```

Verify:

- centered green title with restrained typography
- readable light subtitle and body text
- large scrolling URL editor with muted gutter
- emoji-free premium buttons
- compact visible progress section
- wide activity log with right-side stats rail
- initial values `0`, `0`, `0.0GB`
- green top and bottom/status rules
- native macOS window chrome

- [ ] **Step 3: Mark progress complete**

Update `4Charm.progress.md`:

```text
[x] Task 1: Approve the premium black, white, and green UI design (completed 2026-06-14)
[x] Task 2: Implement the approved UI-only redesign (completed 2026-06-14)
[x] Task 3: Validate behavior, static checks, tests, and the rendered app (completed 2026-06-14)
```

- [ ] **Step 4: Review the final diff**

Run:

```bash
git diff --check
git diff -- src/four_charm/gui/main_window.py src/four_charm/gui/widgets.py src/four_charm/gui/style.qss tests/test_gui.py
git status --short
```

Expected: no whitespace errors and no changes outside the approved UI,
tests/spec/plan/progress, and `.gitignore` scope.
