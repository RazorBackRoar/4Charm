# Building a DMG for 4Charm

4Charm ships as an Apple Silicon `.app` inside `dist/4Charm.dmg`. The primary
build path is the shared RazorBackRoar `razorbuild` pipeline (PyInstaller +
DMG packaging via `Apps/.razorcore/package-dmg.sh`), not a repo-local shell
script. `scripts/package-macos.sh` is the CI fallback and uses the same shared
packager.

## Quick build

From the 4Charm repository root:

```bash
razorbuild 4Charm
# Output: dist/4Charm.dmg
```

In the RazorBackRoar workspace layout, run the same command from `Apps/` after
`uv sync`. If `razorbuild` is on your `PATH` from `.razorcore`, either location
works.

Standalone clones without the full workspace still build when `razorbuild` (or
`4charmbuild`) is installed and `uv sync` has succeeded. GitHub Actions also
packages the Apple Silicon DMG on tag `v*` via `.github/workflows/release.yml`
(`scripts/package-macos.sh`), which uses the shared `package-dmg.sh` for the
locked layout.

## Repo-specific inputs

| File / directory | Purpose |
|------------------|---------|
| `4Charm.spec` | PyInstaller analysis, hidden imports, bundled `assets/` |
| `assets/icons/4Charm.icns` | Dock / Finder icon |
| `assets/dmg-background.png` | DMG background image used by the shared packager if present |
| `assets/dmg-layout.json` | (legacy) no longer read; the shared packager uses the locked `dmg-settings.py` layout |
| `src/four_charm/gui/style.qss` | Bundled Qt stylesheet |

If the packaged app fails to launch, inspect `4Charm.spec` first for missing
assets or hidden-import drift before changing runtime Python code.

## Layout and fallbacks

DMG window geometry is locked workspace-wide in `Apps/.razorcore/dmg-settings.py`
and enforced by `verify-dmg-layout.py`. The shared `package-dmg.sh` (used by
`razorbuild` and `scripts/package-macos.sh`) always produces the locked Finder
window. `create-dmg` and `assets/dmg-layout.json` are no longer used.

## Troubleshooting

| Symptom | What to check |
|---------|---------------|
| Wrong modules at runtime | `4Charm.spec` `hiddenimports` and `datas` |
| Missing icon or stylesheet | `assets/` paths in the spec file |
| DMG window layout off | `assets/dmg-background.png` and the shared `Apps/.razorcore/dmg-settings.py`
| `razorcore` not found locally | Sibling `../.razorcore` for dev; `ci/vendor/` wheel for CI — see [ci/vendor/README.md](../ci/vendor/README.md) |
| Gatekeeper blocks first launch | Right-click → **Open** (ad-hoc signed builds) |

## Related docs

- [BUILD_AND_RELEASE.md](../BUILD_AND_RELEASE.md) — full release checklist
- [README.md](../README.md) — install instructions for end users
