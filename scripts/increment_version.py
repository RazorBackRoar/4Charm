#!/usr/bin/env python3
"""
Automatic version increment script for 4Charm.
Updates version in main.py and setup.py automatically.
Usage:
  ./increment_version.py           # Auto-increment version
  ./increment_version.py --set 4.0.0  # Set specific version
"""

import re
import subprocess
import argparse
import sys
from pathlib import Path


def get_current_version():
    """Get current version from VERSION file or setup.py."""
    version_file = Path("VERSION")
    if version_file.exists():
        return version_file.read_text().strip()
    
    # Fallback to setup.py
    setup_py = Path("setup.py")
    if setup_py.exists():
        content = setup_py.read_text()
        match = re.search(r'"CFBundleVersion": "([^"]+)"', content)
        if match:
            return match.group(1)

    return "0.0.0"


def increment_version(version):
    """Increment version with rollover logic (v3.3.0 -> v3.4.0 -> ... -> v3.9.0 -> v4.0.0)."""
    # Remove 'v' prefix if present
    version = version.lstrip("v")

    parts = version.split(".")
    if len(parts) != 3:
        # If invalid format, default to 0.0.0 logic or raise
        # For robustness, let's try to parse what we can or reset
        if not version:
            return "0.0.1"
        parts = [p for p in parts if p.isdigit()]
        while len(parts) < 3:
            parts.append("0")
        
    major = int(parts[0])
    middle = int(parts[1])
    # Last part is always 0, ignore it

    # Increment middle version
    middle += 1

    # Rollover: if middle reaches 10, reset to 0 and increment major
    if middle >= 10:
        middle = 0
        major += 1

    return f"{major}.{middle}.0"


def update_main_py(new_version):
    """Update version in src/main.py and src/ui/main_window.py."""
    # Update src/main.py
    main_py = Path("src/main.py")
    if main_py.exists():
        content = main_py.read_text()
        content = re.sub(
            r'Version: [0-9.]+',
            f'Version: {new_version}',
            content,
        )
        content = re.sub(
            r'app\.setApplicationVersion\("[^"]+"\)',
            f'app.setApplicationVersion("{new_version}")',
            content,
        )
        main_py.write_text(content)
    
    # Update src/ui/main_window.py
    main_window_py = Path("src/ui/main_window.py")
    if main_window_py.exists():
        content = main_window_py.read_text()
        # Look for version_label = QLabel("v...")
        content = re.sub(
            r'version_label = QLabel\("v[^"]+"\)',
            f'version_label = QLabel("v{new_version}")',
            content,
        )
        main_window_py.write_text(content)



def update_setup_py(new_version):
    """Update version in setup.py."""
    setup_py = Path("setup.py")
    if not setup_py.exists():
        return

    content = setup_py.read_text()
    # Update CFBundleVersion
    content = re.sub(
        r'"CFBundleVersion": "[^"]+"',
        f'"CFBundleVersion": "{new_version}"',
        content,
    )
    # Update CFBundleShortVersionString
    content = re.sub(
        r'"CFBundleShortVersionString": "[^"]+"',
        f'"CFBundleShortVersionString": "{new_version}"',
        content,
    )
    setup_py.write_text(content)


def update_version_file(new_version):
    """Update version in VERSION file."""
    version_file = Path("VERSION")
    version_file.write_text(new_version)


def main():
    """Main function to increment or set version."""
    parser = argparse.ArgumentParser(description="Manage 4Charm version")
    parser.add_argument(
        "--set",
        type=str,
        help="Set a specific version (e.g., --set 4.0.0)",
        metavar="VERSION"
    )
    args = parser.parse_args()

    try:
        old_version = get_current_version()

        if args.set:
            # User specified a version manually
            new_version = args.set.lstrip("v")
            # Validate format
            parts = new_version.split(".")
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                print(f"❌ Invalid version format: {new_version}")
                print("   Expected format: X.Y.Z (e.g., 4.0.0)")
                sys.exit(1)
            print(f"🔄 Setting version: v{old_version} -> v{new_version}")
        else:
            # Auto-increment
            new_version = increment_version(old_version)
            print(f"🔄 Auto-incrementing version: v{old_version} -> v{new_version}")

        update_main_py(new_version)
        update_setup_py(new_version)
        update_version_file(new_version)

        print(f'✅ Updated VERSION file: {new_version}')
        print(f'✅ Updated src/main.py and src/ui/main_window.py')
        print(f'✅ Updated setup.py: CFBundleVersion="{new_version}"')

        return new_version

    except Exception as e:
        print(f"❌ Error managing version: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
