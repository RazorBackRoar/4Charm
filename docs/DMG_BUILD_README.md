# Building a DMG for 4Charm

Use the shared Apps workspace guide:
- [Docs/dmg_build_guide.md](/Users/home/Workspace/Apps/Docs/dmg_build_guide.md)

For 4Charm specifically, run from `/Users/home/Workspace/Apps`:

```bash
uv run --project .razorcore razorbuild 4Charm
```

If `razorbuild` is already on your `PATH`:

```bash
razorbuild 4Charm
```

Repo-specific build inputs:
- [4Charm.spec](/Users/home/Workspace/Apps/4Charm/4Charm.spec)
- app assets under `assets/`

Current notes:
- the primary DMG path is the shared `razorbuild` flow, not a repo-local `build-dmg.sh`
- layout is controlled by the shared build script
- if `create-dmg` is unavailable, the build can still fall back to a plain `hdiutil` DMG without the locked Finder layout

Quick troubleshooting:
- if packaging is wrong, inspect [4Charm.spec](/Users/home/Workspace/Apps/4Charm/4Charm.spec) first
- if DMG layout is wrong, inspect [Docs/dmg_build_guide.md](/Users/home/Workspace/Apps/Docs/dmg_build_guide.md) and [.razorcore/universal-build.sh](/Users/home/Workspace/Apps/.razorcore/universal-build.sh)
- if assets are missing, verify the repo-local `assets/` inputs bundled by `4Charm.spec`
