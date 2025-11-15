#!/usr/bin/env zsh
set -euo pipefail

APP_NAME="4Charm"
PYTHON_EXE="$HOME/.venvs/razor/bin/python"
DIST_DIR="dist"
DMG_STAGING="$DIST_DIR/${APP_NAME}_dmg"
DMG_TEMP="$DIST_DIR/${APP_NAME}_temp.dmg"
DMG_FINAL="$DIST_DIR/${APP_NAME}.dmg"
MOUNT_DIR=""

cleanup() {
  [[ -n "${MOUNT_DIR:-}" ]] && hdiutil detach "$MOUNT_DIR" -force 2>/dev/null || true
}
trap cleanup EXIT

echo "🔨 Building ${APP_NAME}..."

# Clean
rm -rf build "$DIST_DIR" 2>/dev/null || true
mkdir -p "$DIST_DIR"

# Verify & build
"$PYTHON_EXE" -c "import PySide6, requests, bs4" >/dev/null || { echo "❌ Missing deps"; exit 1; }
"$PYTHON_EXE" setup.py py2app > build.log 2>&1
[[ -d "$DIST_DIR/${APP_NAME}.app" ]] || { echo "❌ Build failed"; exit 1; }

# Stage
mkdir -p "$DMG_STAGING"
cp -R "$DIST_DIR/${APP_NAME}.app" "$DMG_STAGING/"
cp LICENSE "$DMG_STAGING/License.txt"
cp README "$DMG_STAGING/"
ln -s /Applications "$DMG_STAGING/Applications"

# Create, mount, layout
hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_STAGING" -ov -format UDRW "$DMG_TEMP"
MOUNT_DIR=$(hdiutil attach "$DMG_TEMP" -nobrowse | awk '/Volumes/{print $3; exit}')

osascript <<EOF
tell app "Finder"
  tell disk "$APP_NAME"
    open
    set current view to icon view
    set toolbar visible to false
    set statusbar visible to false
    set bounds to {100, 100, 600, 600}
    set icon size to 80
    set arrangement to not arranged
    set position of item "${APP_NAME}.app" to {150, 180}
    set position of item "Applications" to {350, 180}
    set position of item "License.txt" to {150, 380}
    set position of item "README" to {350, 380}
    update
    delay 1
    close
  end tell
end tell
EOF

cleanup
sleep 1

# Finish
hdiutil convert "$DMG_TEMP" -format UDZO -o "$DMG_FINAL"
rm -rf "$DMG_STAGING" "$DMG_TEMP"

echo "✅ Done: $DMG_FINAL"
open "$DMG_FINAL"
