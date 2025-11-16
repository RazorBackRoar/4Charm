#!/usr/bin/env zsh

set -euo pipefail
setopt EXTENDED_GLOB NULL_GLOB

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# App configuration
APP_NAME="4Charm"
APP_VERSION="3.0.0"
PYTHON_EXE="$HOME/.venvs/razor/bin/python"
DIST_DIR="dist"
APP_PATH="$DIST_DIR/${APP_NAME}.app"
DMG_FINAL="$DIST_DIR/${APP_NAME}.dmg"
DMG_STAGING="$DIST_DIR/${APP_NAME}_dmg"
DMG_TEMP="$DIST_DIR/${APP_NAME}_temp.dmg"
MOUNT_DIR=""

# Cleanup function - detaches DMG if mounted
cleanup() {
  [[ -n "${MOUNT_DIR:-}" ]] && hdiutil detach "$MOUNT_DIR" -force >/dev/null 2>&1 || true
}
trap cleanup EXIT

log() {
  printf "%b\n" "$1"
}

log "${BLUE}🚀 Building ${APP_NAME} v${APP_VERSION}${NC}"

# --- Pre-Build: Eject any mounted 4Charm volumes ---
log "${YELLOW}0. Checking for mounted 4Charm volumes...${NC}"
# Eject all 4Charm volumes that might be mounted
for vol in /Volumes/4Charm*; do
  if [ -d "$vol" ]; then
    log "${YELLOW}   Ejecting: $vol${NC}"
    hdiutil detach "$vol" -force 2>/dev/null || true
  fi
done
# Also check Desktop for DMG files
if [ -f "/Users/home/Desktop/4Charm.dmg" ]; then
  log "${YELLOW}   Removing old DMG from Desktop${NC}"
  rm -f "/Users/home/Desktop/4Charm.dmg" 2>/dev/null || true
fi
log "${GREEN}✔ Volumes checked and ejected${NC}"

# --- Remove previously installed copies ---
log "${YELLOW}0.5 Removing old application installs...${NC}"
if [[ -d "/Applications/${APP_NAME}.app" ]]; then
  log "${YELLOW}   Deleting /Applications/${APP_NAME}.app${NC}"
  rm -rf -- "/Applications/${APP_NAME}.app"
fi
if [[ -d "$APP_PATH" ]]; then
  log "${YELLOW}   Deleting $APP_PATH${NC}"
  rm -rf -- "$APP_PATH"
fi
log "${GREEN}✔ Old installs removed${NC}"

# --- Build Process ---
log "${YELLOW}1. Cleaning previous builds...${NC}"
# Remove all build artifacts
rm -rf build/ 2>/dev/null || true
rm -rf dist/ 2>/dev/null || true
rm -rf dist_mac/ 2>/dev/null || true
rm -f ${APP_NAME}*.dmg 2>/dev/null || true
rm -f "$DMG_TEMP" 2>/dev/null || true
rm -rf "$DMG_STAGING" 2>/dev/null || true
rm -f build.log *.log 2>/dev/null || true

# Clean Python cache files
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
rm -rf *.egg-info/ 2>/dev/null || true

# Clean macOS files
find . -name ".DS_Store" -delete 2>/dev/null || true

mkdir -p "$DIST_DIR"
log "${GREEN}✔ Clean slate ready${NC}"

log "${YELLOW}2. Verifying dependencies...${NC}"
"$PYTHON_EXE" -c "import PySide6, requests, bs4" >/dev/null
log "${GREEN}✔ Dependencies available${NC}"

log "${YELLOW}3. Building app bundle with py2app...${NC}"
"$PYTHON_EXE" setup.py py2app > build.log 2>&1
log "${GREEN}✔ Application bundle created${NC}"

[[ -d "$APP_PATH" ]] || { log "${RED}❌ Missing ${APP_PATH}${NC}"; exit 1; }

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
rm -f "$DMG_STAGING/.DS_Store"
log "${GREEN}✔ DMG staging ready${NC}"

log "${YELLOW}6. Creating temporary DMG...${NC}"
hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_STAGING" -ov -format UDRW "$DMG_TEMP" >/dev/null 2>&1
MOUNT_DIR=$(hdiutil attach "$DMG_TEMP" -nobrowse | awk '/Volumes/{print $3; exit}')

log "${YELLOW}7. Configuring Finder window layout (2x2 grid, no scrollbars)...${NC}"
osascript <<OSA
tell application "Finder"
  set d to disk "${APP_NAME}"
  open d
  delay 1
  set w to container window of d

  set current view of w to icon view
  set toolbar visible of w to false
  set statusbar visible of w to false
  set bounds of w to {100, 80, 510, 520}
  set icon size of icon view options of w to 72
  set arrangement of icon view options of w to not arranged

  -- 2x2 grid layout - just slightly bigger than 400x400 to avoid scrollbars
  set position of item "${APP_NAME}.app" of w to {105, 105}
  set position of item "Applications" of w to {285, 105}
  set position of item "License.txt" of w to {105, 265}
  set position of item "README" of w to {285, 265}

  update d
  delay 1
  close w
end tell
OSA

cleanup
sleep 1

log "${YELLOW}8. Compressing DMG...${NC}"
hdiutil convert "$DMG_TEMP" -format UDZO -o "$DMG_FINAL" >/dev/null
rm -f "$DMG_TEMP"
rm -rf "$DMG_STAGING"
log "${GREEN}✔ DMG ready at $DMG_FINAL${NC}"

log "${YELLOW}9. Opening DMG in Finder...${NC}"
open "$DMG_FINAL" || log "${YELLOW}⚠️  Unable to auto-open DMG. Path: $DMG_FINAL${NC}"

# --- Summary ---
APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
DMG_SIZE=$(du -sh "$DMG_FINAL" | cut -f1)
log "${BLUE}📦 App size: $APP_SIZE${NC}"
log "${BLUE}📀 DMG size: $DMG_SIZE${NC}"
log "${GREEN}✅ Build complete!${NC}"
