# 4Charm Premium UI Redesign

## Objective

Redesign the existing PySide6 interface into a professional black, white, and
green macOS desktop app while preserving all downloader behavior, URL handling,
statistics, and worker state transitions.

## Approved Direction

Use **Layout A: Focus + Stats Rail** from the visual comparison.

The interface remains a single-window desktop workflow with this hierarchy:

1. Centered 4Charm brand header
2. Large URL entry panel
3. Primary actions
4. Compact progress panel
5. Wide activity log with a right-side statistics rail
6. Bottom engine status bar

## Visual System

- Use near-black and charcoal surfaces as the dominant colors.
- Use soft white for primary text and muted gray for secondary text.
- Reserve bright green for the title, section accents, selected or active
  states, progress fill, success highlights, and statistic values.
- Remove broad neon glows and green body text.
- Use one consistent corner-radius family across panels, inputs, buttons,
  cards, and value pills.
- Use thin neutral borders for containers and subtle green borders only where
  emphasis is useful.
- Add a thin green border across the top of the main content and a green line
  at the bottom/status boundary.
- Use the system sans-serif stack for interface copy and the system monospace
  stack for URLs, logs, and numeric values.

## Window And Header

- Keep the native macOS window chrome.
- Keep `4Charm` centered and green, but reduce weight, glow, and visual bulk.
- Render the subtitle in smaller soft-white or light-gray text.
- Tighten vertical spacing so the header reads as a brand area rather than a
  large empty hero section.
- Preserve the existing minimum window behavior while targeting a balanced
  desktop layout around 1100 by 760 pixels.

## URL Entry

- Keep the composite line-number gutter and `QPlainTextEdit` behavior.
- Increase the practical editor height and preserve clean vertical and
  horizontal scrolling for long pasted lists.
- Use a black editor surface with a subtle green focus/emphasis border.
- Render URLs in soft white and placeholder text in readable gray.
- Keep line numbers muted, compact, and aligned with editor lines.
- Present `URLs to Download` in white with a short green accent bar.
- Keep the queue count visible as quiet supporting metadata.

## Actions

- Keep `Start Download`, `Clear`, and `Folder` visible in an evenly spaced row.
- Keep `Pause`, `Resume`, and `Cancel` behavior available in their existing
  worker states even though those transient controls are not shown in the idle
  mockup.
- Remove emoji from button labels.
- Use a green-accented dark primary button for start and dark neutral secondary
  buttons with subtle borders for the other actions.
- Use green hover and pressed states while retaining white button text.
- Keep existing object names and signal connections where practical.

## Progress

- Use one compact panel containing the section label, status text, speed, and
  progress bar.
- Align the progress/status text left and speed text right.
- Use a dark, clearly visible track with a solid green fill.
- Present concise states such as `Ready`, `Downloading 42%`, and `Complete`.
- Preserve detailed filename, thread, ETA, and speed information when downloads
  are active without increasing the panel height.

## Activity And Statistics

- Place the activity log in the wide left column of the lower area.
- Place `Folders`, `Files`, and `Storage` in a compact vertical rail on the
  right.
- Use white or light-gray log text on black, retaining green only for success or
  positive-status content where the existing text model allows it.
- Keep the log read-only, non-wrapping, padded, rounded, and scrollable.
- Use charcoal stat cards with subtle neutral borders.
- Use lightweight monochrome symbols or no icons; do not use emoji.
- Render labels in white and values in compact green-accented pills.
- Preserve initial values exactly: `0`, `0`, and `0.0GB`.

## Status Bar

- Keep the native `QStatusBar` integration and all existing messages.
- Use readable light text on a black background.
- Add a green top border to separate it from the main content.
- Use green only for the small status indicator or active status emphasis.
- Preserve the initial message `Engine Status: Ready`.

## Implementation Boundaries

Expected source changes are limited to:

- `src/four_charm/gui/main_window.py` for layout, labels, and UI-only state text
- `src/four_charm/gui/widgets.py` for panel, button, and stat-card presentation
- `src/four_charm/gui/style.qss` for the visual system
- `tests/test_gui.py` only for focused UI contract coverage where practical

Do not change:

- downloader or worker logic
- URL extraction, parsing, validation, or paste behavior
- file and folder counting logic
- storage calculations
- output paths
- packaging or dependency configuration

## Validation

The redesign is complete when:

- Existing GUI paste, line-number, and scrolling tests still pass.
- Focused UI tests confirm emoji-free primary labels, initial stat values, and
  the approved log-plus-stats layout.
- `uv run ruff check .` passes.
- `uv run ty check src --python-version 3.14` passes.
- `uv run pytest tests/ -q` passes.
- The app launches locally and visual inspection confirms the black, white, and
  green hierarchy, top and bottom green rules, readable URL editor, polished
  controls, compact progress panel, readable log, and right-side stats rail.

## Non-Goals

- No downloader feature additions.
- No new settings, dialogs, themes, icons, dependencies, or assets.
- No architecture refactor outside the UI composition required for Layout A.
- No packaging, release, version, or repository workflow changes.
