#!/usr/bin/env bash
# Package 4Charm as an Apple Silicon .app and .dmg.
# Requires macOS (hdiutil / codesign). Intended for GitHub Actions macos-15
# and local `razorbuild` fallbacks.
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
STAGE="dist/dmg-stage"
ICON="assets/icons/4Charm.icns"
BACKGROUND="assets/dmg-background.png"

if [[ ! -x ".venv/bin/pyinstaller" ]] && ! command -v uv >/dev/null 2>&1; then
  echo "error: uv is required (https://docs.astral.sh/uv/)" >&2
  exit 1
fi

echo "==> PyInstaller"
rm -rf build dist
uv run pyinstaller --noconfirm --clean "${APP_NAME}.spec"

if [[ ! -d "${APP_PATH}" ]]; then
  echo "error: expected ${APP_PATH} after PyInstaller" >&2
  exit 1
fi

echo "==> Ad-hoc codesign"
codesign --force --deep --sign - "${APP_PATH}"

rm -rf "${STAGE}" "${DMG_PATH}"
mkdir -p "${STAGE}"
cp -R "${APP_PATH}" "${STAGE}/"

echo "==> DMG"
packaged=0
if command -v create-dmg >/dev/null 2>&1; then
  if create-dmg \
    --volname "${APP_NAME}" \
    --volicon "${ICON}" \
    --background "${BACKGROUND}" \
    --window-pos 200 120 \
    --window-size 500 420 \
    --icon-size 96 \
    --icon "${APP_NAME}.app" 130 160 \
    --hide-extension "${APP_NAME}.app" \
    --app-drop-link 370 160 \
    "${DMG_PATH}" \
    "${STAGE}"; then
    packaged=1
  else
    echo "warning: create-dmg failed; falling back to hdiutil" >&2
    rm -f "${DMG_PATH}"
  fi
fi

if [[ "${packaged}" -eq 0 ]]; then
  ln -s /Applications "${STAGE}/Applications"
  hdiutil create \
    -volname "${APP_NAME}" \
    -srcfolder "${STAGE}" \
    -ov \
    -format UDZO \
    "${DMG_PATH}"
fi

if [[ ! -f "${DMG_PATH}" ]]; then
  echo "error: DMG was not created at ${DMG_PATH}" >&2
  exit 1
fi

shasum -a 256 "${DMG_PATH}" | tee dist/4Charm.dmg.sha256
echo "==> Built ${APP_PATH} and ${DMG_PATH}"
