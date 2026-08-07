# Building a DMG for 4Charm

4Charm ships as an Apple Silicon `.app` inside `dist/4Charm.dmg`. The primary
build path is the shared RazorBackRoar `razorbuild` pipeline (PyInstaller +
DMG packaging), not a repo-local shell script.

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
`4charmbuild`) is installed and `uv sync` has succeeded.

## Repo-specific inputs

| File / directory | Purpose |
|------------------|---------|
| `4Charm.spec` | PyInstaller analysis, hidden imports, bundled `assets/` |
| `assets/icons/4Charm.icns` | Dock / Finder icon |
| `assets/dmg-layout.json` | DMG window positions (`app_pos`, `apps_pos`, background) |
| `assets/dmg-background.png` | DMG background image referenced by the layout file |
| `src/four_charm/gui/style.qss` | Bundled Qt stylesheet |

If the packaged app fails to launch, inspect `4Charm.spec` first for missing
assets or hidden-import drift before changing runtime Python code.

## Layout and fallbacks

DMG window geometry is driven by `assets/dmg-layout.json`. The shared
`razorbuild` script applies that layout when `create-dmg` is available. When it
is not, the build can still produce a plain `hdiutil` image without the locked
Finder window — the `.app` remains valid.

## Troubleshooting

| Symptom | What to check |
|---------|---------------|
| Wrong modules at runtime | `4Charm.spec` `hiddenimports` and `datas` |
| Missing icon or stylesheet | `assets/` paths in the spec file |
| DMG window layout off | `assets/dmg-layout.json` and `assets/dmg-background.png` |
| `razorcore` not found locally | Sibling `../.razorcore` for dev; `ci/vendor/` wheel for CI — see [ci/vendor/README.md](../ci/vendor/README.md) |
| Gatekeeper blocks first launch | Right-click → **Open** (ad-hoc signed builds) |

## Related docs

- [BUILD_AND_RELEASE.md](../BUILD_AND_RELEASE.md) — full release checklist
- [README.md](../README.md) — install instructions for end users
