#!/usr/bin/env bash
# Package 4Charm as an Apple Silicon .app and .dmg.
# Uses the shared workspace packager (package-dmg.sh) for the locked 500×420 layout.
# For local runs, package-dmg.sh installs to /Applications and smoke-launches.
# CI/GitHub Actions skips the local handoff.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: macOS packaging must run on macOS (found $(uname -s))" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

APP_NAME="4Charm"
APP_PATH="dist/${APP_NAME}.app"
DMG_PATH="dist/${APP_NAME}.dmg"
RAZORCORE_DIR="$(cd "$ROOT/../.razorcore" && pwd)"

if [[ ! -x ".venv/bin/pyinstaller" ]] && ! command -v uv >/dev/null 2>&1; then
  echo "error: uv is required (https://docs.astral.sh/uv/)" >&2
  exit 1
fi

echo "==> PyInstaller"
rm -rf build dist dist/.previous-build
uv run pyinstaller --noconfirm --clean "${APP_NAME}.spec"

if [[ ! -d "${APP_PATH}" ]]; then
  echo "error: expected ${APP_PATH} after PyInstaller" >&2
  exit 1
fi

echo "==> Branding"
"$RAZORCORE_DIR/patch-app-branding.sh" "${APP_PATH}"

echo "==> Ad-hoc codesign"
codesign --force --deep --sign - "${APP_PATH}"

echo "==> DMG"
"$RAZORCORE_DIR/package-dmg.sh" \
  --app "${APP_PATH}" \
  --dmg "${DMG_PATH}" \
  --app-name "${APP_NAME}" \
  --volname "${APP_NAME}"

if [[ ! -f "${DMG_PATH}" ]]; then
  echo "error: DMG was not created at ${DMG_PATH}" >&2
  exit 1
fi

# Keep only the DMG in-tree — /Applications is the runnable copy.
rm -rf "${APP_PATH}" dist/.previous-build

shasum -a 256 "${DMG_PATH}" | tee dist/4Charm.dmg.sha256
echo "==> Built ${DMG_PATH}"
