#!/usr/bin/env bash
# Package 4Charm as an Apple Silicon .app and .dmg.
# Uses the shared workspace packager (package-dmg.sh) for the locked 500×420 layout.
# Local runs keep dist/<App>.dmg and copy ~/Desktop/<App>.dmg. Do not mount.
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
if [[ -n "${RAZORCORE_DIR:-}" && -d "${RAZORCORE_DIR}" ]]; then
  RAZORCORE_DIR="$(cd "${RAZORCORE_DIR}" && pwd)"
elif [[ -d "$ROOT/../.razorcore" ]]; then
  RAZORCORE_DIR="$(cd "$ROOT/../.razorcore" && pwd)"
else
  echo "error: shared packager not found (set RAZORCORE_DIR or use a sibling Apps/.razorcore)" >&2
  echo "GitHub-hosted runners cannot see private razorcore; build locally with razorbuild 4Charm." >&2
  exit 1
fi

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

# Delete the staging .app.
rm -rf "${APP_PATH}" dist/.previous-build

if [[ ! -f "${DMG_PATH}" ]]; then
  echo "error: DMG was not created at ${DMG_PATH}" >&2
  exit 1
fi

shasum -a 256 "${DMG_PATH}" | tee dist/4Charm.dmg.sha256
echo "==> Built ${DMG_PATH}"
