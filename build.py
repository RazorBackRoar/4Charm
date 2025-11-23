#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import time

# Configuration
APP_NAME = "4Charm"
DIST_DIR = "dist"
BUILD_DIR = "build"
VENV_DIR = os.path.join(BUILD_DIR, "venv")
APP_PATH = os.path.join(DIST_DIR, f"{APP_NAME}.app")
DMG_FINAL = os.path.join(DIST_DIR, f"{APP_NAME}.dmg")
DMG_STAGING = os.path.join(DIST_DIR, f"{APP_NAME}_dmg")
DMG_TEMP = os.path.join(DIST_DIR, f"{APP_NAME}_temp.dmg")

# Colors
GREEN = '\033[0;32m'
YELLOW = '\033[0;33m'
BLUE = '\033[0;34m'
RED = '\033[0;31m'
NC = '\033[0m'

def log(message, color=NC):
    print(f"{color}{message}{NC}")

def run_command(command, shell=False, check=True):
    try:
        subprocess.run(command, shell=shell, check=check, text=True)
    except subprocess.CalledProcessError as e:
        log(f"Error running command: {command}", RED)
        sys.exit(1)

def cleanup():
    # Detach any mounted DMGs
    try:
        result = subprocess.run(["hdiutil", "info"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if APP_NAME in line and "/Volumes/" in line:
                mount_point = line.split("\t")[-1]
                log(f"   Ejecting: {mount_point}", YELLOW)
                subprocess.run(["hdiutil", "detach", mount_point, "-force"], stderr=subprocess.DEVNULL)
    except Exception:
        pass

def main():
    log(f"🚀 Building {APP_NAME}", BLUE)

    # 1. Auto-increment version
    log("1. Auto-incrementing version...", YELLOW)
    if os.path.exists("increment_version.py"):
        try:
            subprocess.run([sys.executable, "increment_version.py"], check=True)
            with open("VERSION", "r") as f:
                version = f.read().strip()
            log(f"✔ Version incremented to: v{version}", GREEN)
        except Exception:
            log("⚠️  Version increment failed", YELLOW)
    
    # 2. Cleanup
    log("2. Cleaning artifacts...", YELLOW)
    cleanup() # Eject volumes
    
    # 2. Cleanup
    log("2. Cleaning artifacts...", YELLOW)
    cleanup() # Eject volumes
    
    # Clean build dir but preserve venv
    if os.path.exists(BUILD_DIR):
        for item in os.listdir(BUILD_DIR):
            if item == "venv":
                continue
            item_path = os.path.join(BUILD_DIR, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

    dirs_to_clean = [DIST_DIR, "dist_mac", DMG_STAGING]
    for d in dirs_to_clean:
        if os.path.exists(d):
            shutil.rmtree(d)
    
    files_to_clean = [DMG_TEMP, "build.log"]
    for f in files_to_clean:
        if os.path.exists(f):
            os.remove(f)
            
    # Clean python cache
    for root, dirs, files in os.walk("."):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d))
        for f in files:
            if f.endswith(".pyc") or f.endswith(".pyo") or f == ".DS_Store":
                os.remove(os.path.join(root, f))
                
    os.makedirs(DIST_DIR, exist_ok=True)
    log("✔ Clean slate ready", GREEN)

    # 3. Build
    log("3. Building app bundle with py2app...", YELLOW)
    # We assume we are running in the venv already or using the system python that has dependencies
    # But build.sh sets up venv. Let's assume this script is called BY build.sh or from the venv.
    
    try:
        with open("build.log", "w") as log_file:
            subprocess.run([sys.executable, "setup.py", "py2app"], stdout=log_file, stderr=subprocess.STDOUT, check=True)
    except subprocess.CalledProcessError:
        log("❌ py2app build failed. Check build.log for details.", RED)
        # Check if app exists anyway
        if os.path.exists(os.path.join(APP_PATH, "Contents/MacOS/4Charm")):
             log("⚠️  py2app reported failure but app bundle exists. Proceeding with caution.", YELLOW)
        else:
            sys.exit(1)

    if not os.path.exists(APP_PATH):
        log(f"❌ Application bundle not found at {APP_PATH}", RED)
        sys.exit(1)
        
    log("✔ Application bundle created", GREEN)

    # 4. Code Signing
    log("4. Code signing (ad-hoc)...", YELLOW)
    run_command(["codesign", "--force", "--deep", "--sign", "-", APP_PATH])
    log("✔ App signed", GREEN)

    # Fixup: py2app might create broken site.pyo symlinks when only site.pyc exists
    resources_dir = os.path.join(APP_PATH, "Contents/Resources")
    site_pyc = os.path.join(resources_dir, "site.pyc")
    site_pyo = os.path.join(resources_dir, "site.pyo")
    if os.path.exists(site_pyc) and not os.path.exists(site_pyo):
        log("   Fixing missing site.pyo (symlinking to site.pyc)...", YELLOW)
        try:
            os.symlink("site.pyc", site_pyo)
        except Exception as e:
            log(f"   Warning: Failed to create site.pyo symlink: {e}", YELLOW)

    # 5. Prepare DMG contents
    log("5. Preparing DMG contents...", YELLOW)
    os.makedirs(DMG_STAGING, exist_ok=True)
    
    # Copy App
    # symlinks=True is important to preserve frameworks structure and avoid following broken links
    shutil.copytree(APP_PATH, os.path.join(DMG_STAGING, f"{APP_NAME}.app"), symlinks=True)
    
    # Copy License and Readme
    if os.path.exists("LICENSE"):
        shutil.copy("LICENSE", os.path.join(DMG_STAGING, "LICENSE.txt"))
    if os.path.exists("README.md"):
        shutil.copy("README.md", os.path.join(DMG_STAGING, "README.md"))
        
    # Create Symlink
    os.symlink("/Applications", os.path.join(DMG_STAGING, "Applications"))
    
    # Remove .DS_Store
    ds_store = os.path.join(DMG_STAGING, ".DS_Store")
    if os.path.exists(ds_store):
        os.remove(ds_store)
        
    log("✔ DMG staging ready", GREEN)

    # 6. Create Temporary DMG
    log("6. Creating temporary DMG...", YELLOW)
    run_command(["hdiutil", "create", "-volname", APP_NAME, "-srcfolder", DMG_STAGING, "-ov", "-format", "UDRW", DMG_TEMP], check=False)
    
    # Mount
    log("   Mounting DMG...", YELLOW)
    mount_output = subprocess.check_output(["hdiutil", "attach", DMG_TEMP, "-nobrowse"]).decode("utf-8")
    mount_point = None
    for line in mount_output.splitlines():
        if "/Volumes/" in line:
            mount_point = line.split("\t")[-1].strip()
            break
            
    if not mount_point:
        log("❌ Failed to mount DMG", RED)
        sys.exit(1)

    # 7. Configure Window Layout
    log("7. Configuring Finder window layout...", YELLOW)
    
    applescript = f'''
    tell application "Finder"
        set d to disk "{APP_NAME}"
        open d
        delay 1
        set w to container window of d
        
        set current view of w to icon view
        set toolbar visible of w to false
        set statusbar visible of w to false
        
        set icon size of icon view options of w to 100
        set arrangement of icon view options of w to not arranged
        
        -- Position items
        set position of item "{APP_NAME}.app" of w to {{140, 120}}
        set position of item "Applications" of w to {{400, 120}}
        set position of item "LICENSE.txt" of w to {{140, 340}}
        set position of item "README.md" of w to {{400, 340}}
        
        -- Set window bounds (x, y, x+width, y+height)
        -- Width: 540, Height: 550
        -- Position: 200, 200
        set bounds of w to {{200, 200, 740, 750}}
        
        update d
        delay 2
        close w
    end tell
    '''
    
    try:
        subprocess.run(["osascript", "-e", applescript], check=True)
    except subprocess.CalledProcessError:
        log("⚠️  Failed to configure window layout via AppleScript", YELLOW)

    # Detach
    log("   Detaching DMG...", YELLOW)
    run_command(["hdiutil", "detach", mount_point, "-force"])
    
    # 8. Compress DMG
    log("8. Compressing DMG...", YELLOW)
    if os.path.exists(DMG_FINAL):
        os.remove(DMG_FINAL)
    run_command(["hdiutil", "convert", DMG_TEMP, "-format", "UDZO", "-o", DMG_FINAL])
    
    # Cleanup temp
    os.remove(DMG_TEMP)
    shutil.rmtree(DMG_STAGING)
    
    log(f"✔ DMG ready at {DMG_FINAL}", GREEN)
    
    # 9. Final Cleanup
    log("9. Cleaning local app bundle copy...", YELLOW)
    if os.path.exists(APP_PATH):
        shutil.rmtree(APP_PATH)
        log(f"✔ Removed build artifact at {APP_PATH}", GREEN)
        
    log(f"📝 Open {DMG_FINAL} manually and drag {APP_NAME}.app into /Applications when you're ready.", BLUE)
    log("✅ Build complete!", GREEN)

if __name__ == "__main__":
    main()
