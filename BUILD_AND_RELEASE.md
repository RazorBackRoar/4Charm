# Build & Release — 4Charm

Organization-standard build and release guide for
[RazorBackRoar/4Charm](https://github.com/RazorBackRoar/4Charm).

## Overview

4Charm is a native macOS app built with **Python 3.14**, **uv**, and
**PySide6**, packaged as an Apple Silicon `.app` / `.dmg`.

## Platform Requirements

| Requirement | Value |
|-------------|-------|
| OS | macOS 12+ (Apple Silicon recommended) |
| Arch | `arm64` |
| Python | **3.14** (uv-managed) |
| Package manager | [uv](https://github.com/astral-sh/uv) — do not use `pip` / `venv` |

## Prerequisites

```zsh
# Install uv if needed: https://docs.astral.sh/uv/
cd /path/to/4Charm
uv sync
```

In the RazorBackRoar workspace layout, `Apps/.razorcore` is an editable sibling
dependency providing shared `razorcore` tooling.

## Development Build

```zsh
uv sync
uv run python -m four_charm.main
```

### Quality gates

```zsh
uv run ruff check .
uv run ty check src --python-version 3.14
uv run pytest tests/ -q
```

CI on `main` runs the same quality job (see `.github/workflows/ci.yml`).

## Packaging

Preferred (workspace tooling):

```zsh
razorbuild 4Charm
# Output: dist/4Charm.dmg
```

`razorbuild` runs the shared PyInstaller + DMG pipeline used by other Python
RazorBackRoar apps.

## Release Process

1. Ensure `main` is green (CI) and the working tree is clean.
2. Confirm the version in `pyproject.toml` matches the intended release.
3. Build the DMG locally: `razorbuild 4Charm`.
4. Smoke-test the packaged DMG (launch, permissions, download test, quit cleanly).
5. Publish the GitHub Release via `razorapps ship` (or `gh release create`).
6. Tag the release to match the version (for example `vX.Y.Z`).

## Versioning Expectations

- Semantic Versioning (`MAJOR.MINOR.PATCH`) in `pyproject.toml`.
- Manifest files are the source of truth — do not hand-edit version strings in
  unrelated docs during a normal save/release flow.
- Workspace version sync may update `Apps/Docs/CONTEXT.md`; keep tables aligned.

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| `uv sync` fails resolving `razorcore` | Ensure sibling `Apps/.razorcore` exists, or use the CI vendor wheel path documented in `ci/` |
| Gatekeeper blocks first launch | Right-click → **Open** (ad-hoc signed builds) |
| PyInstaller missing modules | Rebuild with a clean `dist/` / `build/`; check `*.spec` excludes |
| Tests fail under QThread | Ensure a `QCoreApplication` fixture exists for the suite |

## DMG assets

DMG background art for the release DMG lives under `assets/`:

- `assets/dmg-background.png` — DMG background image used by the shared packager if present
- `assets/dmg-layout.json` — (legacy) no longer read; the locked layout lives in `Apps/.razorcore/dmg-settings.py`

See [docs/DMG_BUILD_README.md](docs/DMG_BUILD_README.md) for packaging
troubleshooting.

## Related Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — download pipeline and module seams
- [README.md](README.md) — product overview
- [CONTRIBUTING.md](CONTRIBUTING.md) — PR workflow
- [SECURITY.md](SECURITY.md) — vulnerability reporting
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — community standards
