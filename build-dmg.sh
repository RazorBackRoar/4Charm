#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="${ROOT_DIR}/dmg-config.json"
APP_PATH="${ROOT_DIR}/dist/4Charm.app"
DIST_DMG_PATH="${ROOT_DIR}/dist/4Charm.dmg"
ROOT_DMG_PATH="${ROOT_DIR}/4Charm.dmg"
VOL_ICON_PATH="${ROOT_DIR}/assets/icons/4Charm.icns"
PYTHON_BIN="/opt/homebrew/bin/python3.13"

if ! command -v create-dmg >/dev/null 2>&1; then
  echo "error: create-dmg is required. Install with: brew install create-dmg" >&2
  exit 1
fi

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "error: missing config file: ${CONFIG_PATH}" >&2
  exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "error: required python not found: ${PYTHON_BIN}" >&2
  exit 1
fi

if [[ ! -d "${APP_PATH}" ]]; then
  echo "error: missing app bundle: ${APP_PATH}" >&2
  echo "build the app first with: ${PYTHON_BIN} -m PyInstaller --clean --noconfirm 4Charm.spec" >&2
  exit 1
fi

if [[ ! -f "${VOL_ICON_PATH}" ]]; then
  echo "error: missing volume icon: ${VOL_ICON_PATH}" >&2
  exit 1
fi

eval "$(
  "${PYTHON_BIN}" - "${CONFIG_PATH}" <<'PY'
import json
import shlex
import sys
from pathlib import Path

cfg = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
window = cfg.get("window", {})
app_icon = cfg.get("app_icon", {})
applications_link = cfg.get("applications_link", {})

values = {
    "VOLUME_NAME": cfg.get("volume_name", "4Charm"),
    "WINDOW_X": window.get("x", 200),
    "WINDOW_Y": window.get("y", 120),
    "WINDOW_WIDTH": window.get("width", 600),
    "WINDOW_HEIGHT": window.get("height", 400),
    "TEXT_SIZE": cfg.get("text_size", 12),
    "ICON_SIZE": cfg.get("icon_size", 100),
    "APP_ICON_NAME": app_icon.get("name", "4Charm.app"),
    "APP_ICON_X": app_icon.get("x", 175),
    "APP_ICON_Y": app_icon.get("y", 180),
    "APP_LINK_X": applications_link.get("x", 425),
    "APP_LINK_Y": applications_link.get("y", 180),
    "HIDE_APP_EXTENSION": "1" if cfg.get("hide_app_extension", True) else "0",
    "FILESYSTEM": cfg.get("filesystem", "HFS+"),
    "DMG_FORMAT": cfg.get("format", "UDZO"),
}

for key, value in values.items():
    print(f"{key}={shlex.quote(str(value))}")
PY
)"

echo "Building DMG with window size ${WINDOW_WIDTH}x${WINDOW_HEIGHT}"

STAGE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/4charm-dmg-stage.XXXXXX")"
cleanup() {
  rm -rf "${STAGE_DIR}"
}
trap cleanup EXIT

cp -R "${APP_PATH}" "${STAGE_DIR}/${APP_ICON_NAME}"
rm -f "${DIST_DMG_PATH}"

DMG_ARGS=(
  --volname "${VOLUME_NAME}"
  --volicon "${VOL_ICON_PATH}"
  --window-pos "${WINDOW_X}" "${WINDOW_Y}"
  --window-size "${WINDOW_WIDTH}" "${WINDOW_HEIGHT}"
  --text-size "${TEXT_SIZE}"
  --icon-size "${ICON_SIZE}"
  --icon "${APP_ICON_NAME}" "${APP_ICON_X}" "${APP_ICON_Y}"
  --app-drop-link "${APP_LINK_X}" "${APP_LINK_Y}"
  --filesystem "${FILESYSTEM}"
  --format "${DMG_FORMAT}"
)

if [[ "${HIDE_APP_EXTENSION}" == "1" ]]; then
  DMG_ARGS+=(--hide-extension "${APP_ICON_NAME}")
fi

create-dmg "${DMG_ARGS[@]}" "${DIST_DMG_PATH}" "${STAGE_DIR}"

cp -f "${DIST_DMG_PATH}" "${ROOT_DMG_PATH}"
open "${DIST_DMG_PATH}"

echo "DMG created: ${DIST_DMG_PATH}"
echo "Mirror copy: ${ROOT_DMG_PATH}"
