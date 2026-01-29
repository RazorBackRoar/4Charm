# 4Charm macOS Build Guide

This guide provides complete instructions for building and distributing the
4Charm macOS application.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Project Structure Verification](#project-structure-verification)
- [Step-by-Step Build Instructions](#step-by-step-build-instructions)
- [Setup.py Configuration](#setuppy-configuration)
- [Code Signing](#code-signing)
- [DMG Creation](#dmg-creation)
- [Release Script Usage](#release-script-usage)
- [GitHub Actions Setup](#github-actions-setup)
- [Quick Command Reference](#quick-command-reference)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before building 4Charm, ensure you have the following tools installed:

### Required Software

#### Python 3.10 or later

```bash
## Check Python version
python3 --version

## Install via Homebrew (if needed)
brew install python@3.10
```

#### py2app (Python to macOS app bundler)

```bash
pip install py2app
```

#### create-dmg (DMG installer creator)

```bash
brew install create-dmg
```

#### Xcode Command Line Tools (for code signing)

```bash
xcode-select --install
```

### Python Dependencies

Install all required Python packages:

```bash
pip install PySide6 requests urllib3 certifi
```

### Verify Installation

Check that all tools are available:

```bash
## Verify py2app
python3 -c "import py2app; print('py2app installed')"

## Verify create-dmg
which create-dmg

## Verify codesign
which codesign
```

## Project Structure Verification

Before building, verify your project has the correct structure:

```text
4Charm/
├── main.py                          # Application entry point
├── resources/
│   └── 4Charm.icns                  # Application icon
├── setup.py                         # py2app configuration
├── build.sh                         # Build automation script (py2app + DMG)
├── LICENSE                          # MIT License
└── README.md                        # Project README
```

### Check Required Files

```bash
## Verify main.py exists
test -f main.py && echo "✓ main.py found" || echo "✗ main.py missing"

## Verify icon file exists
test -f resources/4Charm.icns && echo "✓ Icon found" || echo "✗ Icon missing"

## Verify setup.py exists
test -f setup.py && echo "✓ setup.py found" || echo "✗ setup.py missing"
```

## Step-by-Step Build Instructions

### 0. Quick Build (Recommended)

To perform a full clean build (app bundle + DMG) in one step, run:

```bash
./build.sh
```

This script will:

- Clean previous build artifacts (build, dist, DMGs, caches)
- Run `py2app` to create `dist/4Charm.app`
- Ad-hoc sign the app with `codesign`
- Create `dist/4Charm.dmg` with the 2×2 Finder layout

The sections below document the **equivalent manual commands** that `build.sh`
performs.

### 1. Clean Previous Builds

Remove any existing build artifacts:

```bash
rm -rf build dist
```

### 2. Build the App Bundle

Run py2app to create the .app bundle:

```bash
python3 setup.py py2app
```

This will:

- Analyze dependencies in main.py
- Bundle Python interpreter and libraries
- Create `dist/4Charm.app` with all resources
- Generate Info.plist with bundle metadata
- Copy icon to Resources directory

Expected output:

```text
creating dist/4Charm.app
copying resources -> dist/4Charm.app/Contents/Resources
creating application bundle
done
```

### 3. Sign the Application

Apply ad-hoc code signing:

```bash
codesign --force --deep --sign - dist/4Charm.app
```

Verify the signature:

```bash
codesign --verify --deep --verbose=2 dist/4Charm.app
```

### 4. Create the DMG Installer

If you use `./build.sh`, the script will automatically:

- Stage `4Charm.app`, `License.txt`, and `README`
- Create a temporary DMG with `hdiutil`
- Set the Finder window to a compact 2×2 layout
- Convert it to a compressed DMG at `dist/4Charm.dmg`

If you prefer to create a DMG manually (advanced use or CI), you can also use
`create-dmg` as shown below:

```bash
create-dmg \
  --volname "4Charm" \
  --volicon "resources/4Charm.icns" \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "4Charm.app" 175 120 \
  --app-drop-link 425 120 \
  --eula LICENSE.rtf \
  --codesign "-" \
  "4Charm_1.0.0.dmg" \
  "dist/4Charm.app"
```

### 5. Test the Build

Mount and test the DMG:

```bash
## Mount the DMG
open 4Charm_1.0.0.dmg

## After mounting, test the app
open /Volumes/4Charm/4Charm.app
```

## Setup.py Configuration

The `setup.py` file configures py2app for building 4Charm. Here's the complete
configuration:

```python
from setuptools import setup

APP = ['main.py']
DATA_FILES = [

```
('resources', ['resources/4Charm.icns']),

```text

]

OPTIONS = {

```
'argv_emulation': False,
'iconfile': 'resources/4Charm.icns',
'packages': ['PySide6', 'requests', 'urllib3', 'certifi'],
'includes': [
'PySide6.QtCore',
'PySide6.QtWidgets',
'PySide6.QtGui',
],
'excludes': [
'PyQt6',
'PyQt5',
'tkinter',
'test',
'unittest',
],
'plist': {
'CFBundleName': '4Charm',
'CFBundleDisplayName': '4Charm',
'CFBundleVersion': '1.0.0',
'CFBundleShortVersionString': '1.0.0',
'CFBundleIdentifier': 'com.RazorBackRoar.4Charm',
'NSHighResolutionCapable': True,
'NSRequiresAquaSystemAppearance': False,
}

```text

}

setup(

```
app=APP,
name='4Charm',
data_files=DATA_FILES,
options={'py2app': OPTIONS},
setup_requires=['py2app'],

```text

)
```

### Key Configuration Options

#### Entry Point

- `APP = ['main.py']` - Specifies the main Python file to bundle

#### Resources

- `DATA_FILES` - Includes the icon file in the bundle

#### Bundle Metadata (plist)

- `CFBundleName` - Internal bundle name
- `CFBundleDisplayName` - Name shown in Finder and menu bar
- `CFBundleIdentifier` - Unique identifier (reverse domain notation)
- `CFBundleVersion` - Build version number
- `CFBundleShortVersionString` - User-visible version
- `NSHighResolutionCapable` - Enables Retina display support
- `NSRequiresAquaSystemAppearance` - Set to False for dark mode support

#### Dependencies

- `packages` - Python packages to include
- `includes` - Specific modules to ensure are bundled
- `excludes` - Packages to exclude (reduces bundle size)

#### Special Settings

- `argv_emulation: False` - Prevents command-line argument issues in bundled

  apps

## Code Signing

### Ad-hoc Signing (Free)

4Charm uses ad-hoc signing, which doesn't require an Apple Developer account:

```bash
codesign --force --deep --sign - dist/4Charm.app
```

#### Parameters

- `--force` - Replace existing signature if present
- `--deep` - Sign all nested code (frameworks, libraries)
- `--sign -` - Use ad-hoc signature (no certificate)

### Verify Signature

```bash
## Basic verification
codesign --verify dist/4Charm.app

## Detailed verification
codesign --verify --deep --verbose=2 dist/4Charm.app

## Display signature information
codesign --display --verbose=4 dist/4Charm.app
```

### Limitations of Ad-hoc Signing

**Pros:**

- Free (no Apple Developer Program required)
- Allows app to run on macOS
- Prevents tampering

**Cons:**

- Shows security warning on first launch
- Cannot be notarized by Apple
- Requires user to right-click → Open

### Upgrading to Developer ID Signing

For production releases, consider purchasing an Apple Developer account
($99/year):

```bash
## Sign with Developer ID
codesign --force --deep --sign "Developer ID Application: Your Name" dist/4Charm.app

## Notarize the app
xcrun notarytool submit 4Charm_1.0.0.dmg --apple-id your@email.com --password app-specific-password --team-id TEAMID

## Staple notarization ticket
xcrun stapler staple dist/4Charm.app
```

## DMG Creation

### Basic DMG Creation

```bash
create-dmg \
  --volname "4Charm" \
  --volicon "resources/4Charm.icns" \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "4Charm.app" 175 120 \
  --app-drop-link 425 120 \
  "4Charm_1.0.0.dmg" \
  "dist/4Charm.app"
```

### DMG Options Explained

#### Volume Settings

- `--volname "4Charm"` - Name shown when DMG is mounted
- `--volicon "resources/4Charm.icns"` - Custom volume icon

#### Window Layout

- `--window-size 600 400` - DMG window dimensions (pixels)
- `--icon-size 100` - Size of icons in the window

#### Icon Positioning

- `--icon "4Charm.app" 175 120` - Position of app icon (x, y)
- `--app-drop-link 425 120` - Position of Applications folder link

#### Additional Options

- `--eula LICENSE.rtf` - Display license agreement on mount
- `--codesign "-"` - Apply ad-hoc signing to the DMG
- `--background image.png` - Custom background image (optional)

### Advanced DMG Customization

For a custom background image:

```bash
create-dmg \
  --volname "4Charm" \
  --volicon "resources/4Charm.icns" \
  --background "resources/dmg-background.png" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "4Charm.app" 175 120 \
  --app-drop-link 425 120 \
  --eula LICENSE.rtf \
  --codesign "-" \
  "4Charm_1.0.0.dmg" \
  "dist/4Charm.app"
```

## Release Script Usage

The `release.sh` script automates the entire build process.

### Basic Usage

```bash
## Build with default version (1.0.0)
./release.sh

## Build with specific version
./release.sh 1.2.3
```

### Script Workflow

The script performs these steps automatically:

1. Cleans previous builds (`rm -rf build dist`)
2. Builds app bundle (`python3 setup.py py2app`)
3. Signs the application (`codesign`)
4. Creates DMG installer (`create-dmg`)
5. Reports success with output filename

### Make Script Executable

If you get a permission error:

```bash
chmod +x release.sh
```

### Script Output

Successful build output:

```text
Building 4Charm v1.0.0...
Cleaning previous builds...
Building app bundle...
Signing application...
Creating DMG...
✅ Build complete: 4Charm_1.0.0.dmg
```

### Error Handling

The script uses `set -e` to exit immediately on any error. If a step fails:

1. Check the error message
2. Verify prerequisites are installed
3. Ensure required files exist
4. See [Troubleshooting](#troubleshooting) section

## GitHub Actions Setup

### Workflow Configuration

Create `.github/workflows/release.yml`:

```yaml
name: Build and Release DMG

on:
  push:

```
tags:
- 'v*'

```text

jobs:
  build:

```
runs-on: macos-latest

```text

```
steps:
- name: Checkout code
uses: actions/checkout@v3

```text

```
- name: Setup Python
uses: actions/setup-python@v4
with:
python-version: '3.10'

```text

      - name: Install Python dependencies
        run: |
          pip install py2app PySide6 requests urllib3 certifi

      - name: Install create-dmg
        run: |
          brew install create-dmg

      - name: Build app bundle
        run: |
          python3 setup.py py2app

      - name: Sign application
        run: |
          codesign --force --deep --sign - dist/4Charm.app

      - name: Extract version from tag
        id: get_version
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT

      - name: Create DMG
        run: |
          create-dmg \
            --volname "4Charm ${{ steps.get_version.outputs.VERSION }}" \
            --volicon "resources/4Charm.icns" \
            --window-size 600 400 \
            --icon-size 100 \
            --icon "4Charm.app" 175 120 \
            --app-drop-link 425 120 \
            --eula LICENSE.rtf \
            --codesign "-" \
            "4Charm_${{ steps.get_version.outputs.VERSION }}.dmg" \
            "dist/4Charm.app"

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: 4Charm_*.dmg
          draft: false
          prerelease: false
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Triggering a Release

1. **Commit all changes:**

```bash
   git add .
   git commit -m "Release v1.0.0"
```

2. **Create a version tag:**

```bash
   git tag v1.0.0
```

3. **Push the tag:**

```bash
   git push origin v1.0.0
```

4. **Monitor the workflow:**
   - Go to GitHub repository → Actions tab
   - Watch the build progress
   - Download DMG from Releases page when complete

### Workflow Features

- **Automatic triggering** - Runs when you push a tag starting with `v`
- **Version extraction** - Uses tag name as version number
- **Artifact upload** - Automatically uploads DMG to GitHub Releases
- **macOS runner** - Builds on latest macOS for compatibility

### Testing the Workflow

Before creating a real release, test with a pre-release tag:

```bash
git tag v0.9.0-beta
git push origin v0.9.0-beta
```

Then delete the test release and tag:

```bash
## Delete remote tag
git push --delete origin v0.9.0-beta

## Delete local tag
git tag -d v0.9.0-beta
```

## Quick Command Reference

### Complete Build Process

```bash
## One-line build (using release script)
./release.sh 1.0.0

## Manual build steps
rm -rf build dist
python3 setup.py py2app
codesign --force --deep --sign - dist/4Charm.app
create-dmg --volname "4Charm" --volicon "resources/4Charm.icns" \
  --window-size 600 400 --icon-size 100 \
  --icon "4Charm.app" 175 120 --app-drop-link 425 120 \
  --codesign "-" "4Charm_1.0.0.dmg" "dist/4Charm.app"
```

### Verification Commands

```bash
## Verify app bundle structure
ls -la dist/4Charm.app/Contents/MacOS/
ls -la dist/4Charm.app/Contents/Resources/

## Verify code signature
codesign --verify --deep dist/4Charm.app

## Check bundle info
plutil -p dist/4Charm.app/Contents/Info.plist

## Test app launch
open dist/4Charm.app
```

### Cleanup Commands

```bash
## Remove build artifacts
rm -rf build dist

## Remove DMG files
rm -f *.dmg

## Complete cleanup
rm -rf build dist *.dmg
```

### Git Release Commands

```bash
## Create and push release tag
git tag v1.0.0
git push origin v1.0.0

## List all tags
git tag -l

## Delete tag (if needed)
git tag -d v1.0.0
git push --delete origin v1.0.0
```

## Troubleshooting

### py2app Not Installed

#### Error (py2app)

```text
ModuleNotFoundError: No module named 'py2app'
```

#### Solution (py2app)

```bash
pip install py2app
```

### create-dmg Not Installed

#### Error (create-dmg missing)

```text
command not found: create-dmg
```

#### Solution (create-dmg install)

```bash
brew install create-dmg
```

### Missing main.py

#### Error (missing main.py)

```text
error: [Errno 2] No such file or directory: 'main.py'
```

#### Solution

- Verify you're in the project root directory
- Ensure main.py exists: `ls -la main.py`
- Check setup.py has correct APP entry point

### Missing Icon File

#### Error (missing icon)

```text
error: [Errno 2] No such file or directory: 'resources/4Charm.icns'
```

#### Solution (missing icon)

```bash
## Check if icon exists
ls -la resources/4Charm.icns

## Create resources directory if missing
mkdir -p resources

## Ensure icon file is present
```

### Code Signing Failure

#### Error (code signing)

```text
code object is not signed at all
```

#### Solution (code signing)

```bash
## Ensure Xcode Command Line Tools are installed
xcode-select --install

## Try signing again with verbose output
codesign --force --deep --sign - --verbose=4 dist/4Charm.app
```

### DMG Creation Fails

#### Error (create-dmg failure)

```text
create-dmg: command failed with exit code 1
```

#### Solutions (create-dmg failure)

1. **Check if DMG already exists:**

```bash
   rm -f 4Charm_1.0.0.dmg
```

2. **Verify app bundle exists:**

```bash
   ls -la dist/4Charm.app
```

3. **Check disk space:**

```bash
   df -h .
```

### Insufficient Disk Space

#### Error (disk space)

```text
OSError: [Errno 28] No space left on device
```

#### Solution (disk space)

```bash
## Check available space
df -h

## Clean up old builds
rm -rf build dist *.dmg

## Free up space on your system
```

### App Won't Launch

#### Issue (app launch)

Double-clicking the app does nothing or shows an error.

#### Solutions (app launch)

1. **Check for crash logs:**

```bash
   open ~/Library/Logs/DiagnosticReports/
```

2. **Run from terminal to see errors:**

```bash
   dist/4Charm.app/Contents/MacOS/4Charm
```

3. **Verify all dependencies are bundled:**

```bash
   ls -la dist/4Charm.app/Contents/Resources/lib/python3.*/
```

4. **Check Info.plist is valid:**

```bash
   plutil -lint dist/4Charm.app/Contents/Info.plist
```

### Gatekeeper Blocks App

#### Issue (Gatekeeper)

macOS shows "4Charm cannot be opened because it is from an unidentified
developer"

#### Solutions (Gatekeeper)

1. **Right-click → Open method:**

   - Right-click (or Control-click) on 4Charm.app
   - Select "Open" from the menu
   - Click "Open" in the security dialog

2. **Remove quarantine attribute:**

```bash
   xattr -cr /Applications/4Charm.app
```

3. **System Settings method:**
   - Open System Settings → Privacy & Security
   - Scroll to "Security" section
   - Click "Open Anyway" next to 4Charm message

### GitHub Actions Workflow Fails

#### Issue (GitHub Actions)

CI/CD build fails on GitHub

#### Debugging steps (GitHub Actions)

1. **Check workflow logs:**

   - Go to Actions tab in GitHub
   - Click on failed workflow
   - Review each step's output

2. **Common issues:**

   - Missing files in repository
   - Incorrect file paths
   - Python version mismatch
   - Missing dependencies

3. **Test locally first:**

```bash
   # Ensure local build works
   ./release.sh
```

### Python Version Mismatch

#### Error (python version)

```text
RuntimeError: Python 3.10 or later is required
```

#### Solution (python version)

```bash
## Check Python version (2)
python3 --version

## Install correct version via Homebrew
brew install python@3.10

## Update PATH if needed
export PATH="/usr/local/opt/python@3.10/bin:$PATH"
```

### Bundle Size Too Large

#### Issue (bundle size)

App bundle is over 300 MB

#### Solutions (bundle size)

1. **Check what's included:**

```bash
   du -sh dist/4Charm.app/*
```

2. **Add more exclusions to setup.py:**

```python
   'excludes': [
       'PyQt6', 'PyQt5', 'tkinter',
       'test', 'unittest', 'email',
       'xml', 'pydoc', 'doctest',
   ]
```

3. **Enable optimization:**

```python
   OPTIONS = {
       'optimize': 2,
       'compressed': True,
       # ... other options
   }
```

---

## Additional Resources

- [py2app Documentation](https://py2app.readthedocs.io/)
- [create-dmg GitHub](https://github.com/create-dmg/create-dmg)
- [Apple Code Signing Guide](https://developer.apple.com/support/code-signing/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## Support

For issues specific to 4Charm, please open an issue on the GitHub repository.
