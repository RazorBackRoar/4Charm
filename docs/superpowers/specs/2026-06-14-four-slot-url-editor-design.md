# 4Charm Four-Slot URL Editor

## Objective

Make the 4Charm window more compact while giving the URL editor four prominent,
evenly spaced slots that match the app name.

## Approved Design

- Default window size: 1280 by 820 pixels.
- Minimum window height: no more than 780 pixels.
- Empty URL gutter: show `1` through `4`.
- URL editor height: 120 pixels.
- URL rows: use 200% proportional line height so pasted URLs appear
  double-spaced without inserting blank text lines.
- Pasted URLs remain stored one per actual document line.
- Queue counts and downloader input continue to ignore empty lines.
- More than four URLs remain supported through the existing scrollbar and
  dynamically extended line-number gutter.

## Scope

Modify only:

- `src/four_charm/gui/main_window.py`
- `src/four_charm/gui/widgets.py`
- `src/four_charm/gui/style.qss`
- `tests/test_gui.py`
- UI progress and design-QA documentation

Do not change downloader behavior, validation rules, output paths, packaging
configuration, dependencies, or visual colors.

## Validation

- A four-URL paste produces four document blocks, four queue entries, and
  gutter labels `1` through `4`.
- Empty state displays four gutter labels.
- The editor uses 200% proportional line height.
- The default window is 1280 by 820 and remains usable at its minimum size.
- Existing large-paste scrolling and manual-entry behavior continue to pass.
- Ruff, ty, the full test suite, DMG build, signature verification, and
  packaged visual inspection pass.
