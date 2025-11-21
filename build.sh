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
APP_VERSION="4.1.0"
VENV_DIR="build/venv"
PYTHON_EXE="$VENV_DIR/bin/python"
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

# --- Setup Build Environment ---
log "${YELLOW}0. Setting up build environment...${NC}"
# Clean previous builds first to ensure fresh venv
rm -rf build/ 2>/dev/null || true
rm -rf dist/ 2>/dev/null || true
rm -rf dist_mac/ 2>/dev/null || true
rm -f ${APP_NAME}*.dmg 2>/dev/null || true
rm -f "$DMG_TEMP" 2>/dev/null || true
rm -rf "$DMG_STAGING" 2>/dev/null || true
rm -f build.log *.log 2>/dev/null || true

# Create venv
log "${YELLOW}   Creating virtual environment...${NC}"
/opt/homebrew/bin/python3.13 -m venv "$VENV_DIR"

# Install dependencies
log "${YELLOW}   Installing dependencies...${NC}"
"$PYTHON_EXE" -m pip install --upgrade pip >/dev/null
"$PYTHON_EXE" -m pip install -r requirements.txt >/dev/null
"$PYTHON_EXE" -m pip install py2app >/dev/null

log "${GREEN}✔ Build environment ready${NC}"

# Read version from VERSION file (gitignored, won't show in source control)
if [[ -f "VERSION" ]]; then
  APP_VERSION=$(cat VERSION)
fi

log "${YELLOW}1. Auto-incrementing version...${NC}"
if "$PYTHON_EXE" increment_version.py >/dev/null 2>&1; then
  APP_VERSION=$(cat VERSION)
  log "${GREEN}✔ Version incremented to: v${APP_VERSION}${NC}"
else
  log "${YELLOW}⚠️  Version increment failed, using current version: v${APP_VERSION}${NC}"
fi

# --- Pre-Build: Eject any mounted 4Charm volumes ---
log "${YELLOW}2. Checking for mounted 4Charm volumes...${NC}"
# Eject all 4Charm volumes that might be mounted
for vol in /Volumes/4Charm*; do
  if [ -d "$vol" ]; then
    log "${YELLOW}   Ejecting: $vol${NC}"
    hdiutil detach "$vol" -force 2>/dev/null || true
  fi
done
# Also check Desktop for DMG files
if [ -f "$HOME/Desktop/4Charm.dmg" ]; then
  log "${YELLOW}   Removing old DMG from Desktop${NC}"
  rm -f "$HOME/Desktop/4Charm.dmg" 2>/dev/null || true
fi
log "${GREEN}✔ Volumes checked and ejected${NC}"

# --- Remove previously installed copies ---
log "${YELLOW}3. Removing old application installs...${NC}"
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
log "${YELLOW}4. Cleaning artifacts...${NC}"
# Clean Python cache files
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
rm -rf *.egg-info/ 2>/dev/null || true

# Clean macOS files
find . -name ".DS_Store" -delete 2>/dev/null || true

mkdir -p "$DIST_DIR"
log "${GREEN}✔ Clean slate ready${NC}"

log "${YELLOW}5. Building app bundle with py2app...${NC}"
if ! "$PYTHON_EXE" setup.py py2app > build.log 2>&1; then
  log "${RED}❌ py2app build failed. Check build.log for details.${NC}"
  # Check if app exists despite failure (sometimes import check fails but app is fine)
  if [[ -d "$APP_PATH" && -f "$APP_PATH/Contents/MacOS/4Charm" ]]; then
      log "${YELLOW}⚠️  py2app reported failure but app bundle exists. Proceeding with caution.${NC}"
  else
      exit 1
  fi
fi

# Validate app bundle was created
if [[ ! -d "$APP_PATH" ]]; then
  log "${RED}❌ Application bundle not found at $APP_PATH${NC}"
  exit 1
fi

# Validate app bundle contains main executable
if [[ ! -f "$APP_PATH/Contents/MacOS/4Charm" ]]; then
  log "${RED}❌ Main executable not found in app bundle${NC}"
  exit 1
fi

log "${GREEN}✔ Application bundle created and validated${NC}"

log "${YELLOW}6. Code signing (ad-hoc)...${NC}"
if ! codesign --force --deep --sign - "$APP_PATH"; then
  log "${RED}❌ Code signing failed${NC}"
  exit 1
fi
log "${GREEN}✔ App signed${NC}"

log "${YELLOW}7. Preparing DMG contents...${NC}"
rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"
cp -R "$APP_PATH" "$DMG_STAGING/"
cp LICENSE "$DMG_STAGING/License.txt"
cp README "$DMG_STAGING/README"
ln -s /Applications "$DMG_STAGING/Applications"
rm -f "$DMG_STAGING/.DS_Store"
log "${GREEN}✔ DMG staging ready${NC}"

log "${YELLOW}8. Creating temporary DMG...${NC}"
hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_STAGING" -ov -format UDRW "$DMG_TEMP" >/dev/null 2>&1
MOUNT_DIR=$(hdiutil attach "$DMG_TEMP" -nobrowse | awk '/Volumes/{print $3; exit}')

log "${YELLOW}9. Configuring Finder window layout (2x2 grid, no scrollbars)...${NC}"
osascript <<OSA
tell application "Finder"
  set d to disk "${APP_NAME}"
  open d
  delay 1
  set w to container window of d

  set current view of w to icon view
  set toolbar visible of w to false
  set statusbar visible of w to false
  set icon size of icon view options of w to 72
  set arrangement of icon view options of w to not arranged

  -- 2x2 grid layout - 400x430 window (extra height for labels)
  set position of item "${APP_NAME}.app" of w to {100, 100}
  set position of item "Applications" of w to {260, 100}
  set position of item "License.txt" of w to {100, 230}
  set position of item "README" of w to {260, 230}

  -- Set bounds AFTER positioning items - 400 wide x 430 tall to avoid scrollbars
  set bounds of w to {100, 100, 500, 530}
  update d
  delay 2
  close w
end tell
OSA

cleanup
sleep 1

log "${YELLOW}10. Compressing DMG...${NC}"
hdiutil convert "$DMG_TEMP" -format UDZO -o "$DMG_FINAL" >/dev/null
rm -f "$DMG_TEMP"
rm -rf "$DMG_STAGING"
log "${GREEN}✔ DMG ready at $DMG_FINAL${NC}"

log "${YELLOW}11. Opening DMG in Finder...${NC}"
open "$DMG_FINAL" || log "${YELLOW}⚠️  Unable to auto-open DMG. Path: $DMG_FINAL${NC}"

# --- Summary ---
APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
DMG_SIZE=$(du -sh "$DMG_FINAL" | cut -f1)
log "${BLUE}📦 App size: $APP_SIZE${NC}"
log "${BLUE}📀 DMG size: $DMG_SIZE${NC}"
log "${GREEN}✅ Build complete!${NC}"
