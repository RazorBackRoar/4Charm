#!/bin/bash
set -e  # Exit on any error

echo "Building 4Charm..."

# Setup Python 3.13 virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python 3.13 virtual environment..."
    python3.13 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install PySide6 requests pyinstaller pillow
else
    source venv/bin/activate
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist *.dmg *.spec __pycache__

# Build app bundle with PyInstaller
echo "Building app bundle..."
pyinstaller \
  --clean \
  --name="4Charm" \
  --windowed \
  --onedir \
  --noconfirm \
  --icon="resources/4Charm.icns" \
  --osx-bundle-identifier="com.4charm.app" \
  --add-data="resources:resources" \
  main.py

# Sign the app bundle
echo "Signing app bundle..."
codesign --force --deep --sign - dist/4Charm.app

# Copy LICENSE and Info files to dist folder for DMG
echo "Adding LICENSE and README to DMG..."
cp LICENSE.rtf dist/
cp README dist/

# Create DMG installer
echo "Creating DMG installer..."
create-dmg \
  --volname "4Charm" \
  --volicon "resources/4Charm.icns" \
  --window-size 400 380 \
  --icon-size 72 \
  --icon "4Charm.app" 100 80 \
  --icon "README" 280 80 \
  --icon "LICENSE.rtf" 100 220 \
  --app-drop-link 280 220 \
  --codesign "-" \
  "4Charm.dmg" \
  "dist/"

echo "✅ Build complete: 4Charm.dmg"
