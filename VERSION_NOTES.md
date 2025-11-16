# Version Update Instructions

When updating the 4Charm version number, you must update it in **THREE** locations:

## 1. setup.py (Line 18-19)

```python
'CFBundleVersion': '3.0.0',
'CFBundleShortVersionString': '3.0.0',
```

## 2. main.py (Line ~1215)

```python
# Version label (bottom right)
version_label = QLabel("v3.0.0")
```

This displays the version in the bottom right of the app UI.

## 3. Build Output

The DMG filename will be automatically named `4Charm.dmg` (no version in filename).

---

## Current Version: 3.0.0

**Last Updated:** November 15, 2025
