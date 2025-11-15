#!/usr/bin/env zsh

set -euo pipefail
setopt EXTENDED_GLOB NULL_GLOB

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

APP_NAME="4Charm"
APP_VERSION="3.0.0"
PYTHON_EXE="$HOME/.venvs/razor/bin/python"
DIST_DIR="dist"
APP_PATH="$DIST_DIR/${APP_NAME}.app"
DMG_PATH="$DIST_DIR/${APP_NAME}.dmg"
DMG_STAGING="$DIST_DIR/${APP_NAME}_dmg"
DMG_TEMP="$DIST_DIR/${APP_NAME}_temp.dmg"
MOUNT_DIR=""

cleanup() {
  if [[ -n "$MOUNT_DIR" ]]; then
    hdiutil detach "$MOUNT_DIR" -force >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

log() {
  printf "%b\n" "$1"
}

log "${BLUE}🚀 Building ${APP_NAME} v${APP_VERSION}${NC}"

log "${YELLOW}1. Cleaning previous builds...${NC}"
rm -rf \
  build \
  "$DIST_DIR" \
  ${APP_NAME}*.dmg \
  "$DMG_TEMP" \
  "$DMG_STAGING" \
  build.log \
  __pycache__ \
  .DS_Store \
  "$DIST_DIR"/.DS_Store \
  2>/dev/null || true
mkdir -p "$DIST_DIR"
log "${GREEN}✔ Clean slate ready${NC}"

log "${YELLOW}2. Verifying dependencies...${NC}"
"$PYTHON_EXE" -c "import PySide6, requests, bs4" >/dev/null
log "${GREEN}✔ Dependencies available${NC}"

log "${YELLOW}3. Building app bundle with py2app...${NC}"
"$PYTHON_EXE" setup.py py2app > build.log 2>&1
log "${GREEN}✔ Application bundle created${NC}"

if [[ ! -d "$APP_PATH" ]]; then
  log "${RED}❌ Missing ${APP_PATH}${NC}"
  exit 1
fi

log "${YELLOW}4. Code signing (ad-hoc)...${NC}"
codesign --force --deep --sign - "$APP_PATH"
log "${GREEN}✔ App signed${NC}"

log "${YELLOW}5. Preparing DMG contents...${NC}"
rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"
cp -R "$APP_PATH" "$DMG_STAGING/"
cp LICENSE "$DMG_STAGING/License.txt"
cp README "$DMG_STAGING/README"
ln -s /Applications "$DMG_STAGING/Applications"
log "${GREEN}✔ DMG staging ready${NC}"

log "${YELLOW}6. Creating temporary writable DMG...${NC}"
hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_STAGING" -ov -format UDRW "$DMG_TEMP" >/dev/null
MOUNT_DIR=$(hdiutil attach "$DMG_TEMP" | awk '/Volumes/{print $3; exit}')

log "${YELLOW}7. Configuring Finder window (2x2 layout)...${NC}"
osascript <<OSA
tell application "Finder"
  tell disk "${APP_NAME}"
    open
    set current view of container window to icon view
    set toolbar visible of container window to false
    set statusbar visible of container window to false
    set the bounds of container window to {100, 100, 580, 420}
    set icon size of the icon view options of container window to 72
    delay 1
  end tell
end tell
OSA

cleanup
trap - EXIT
MOUNT_DIR=""
trap cleanup EXIT
sleep 2

log "${YELLOW}8. Compressing DMG...${NC}"
hdiutil convert "$DMG_TEMP" -format UDZO -o "$DMG_PATH" >/dev/null
rm -f "$DMG_TEMP"
rm -rf "$DMG_STAGING"
log "${GREEN}✔ DMG ready at $DMG_PATH${NC}"

APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1)

log "${BLUE}📦 App size: $APP_SIZE${NC}"
log "${BLUE}📀 DMG size: $DMG_SIZE${NC}"
log "${GREEN}✅ Build complete!${NC}"
