#!/usr/bin/env python3
"""
Automatic version increment script for 4Charm.
Updates version in build.sh and main.py automatically.
"""

import re
import subprocess
from pathlib import Path


def get_current_version():
    """Get current version from build.sh."""
    build_sh = Path("build.sh")
    if not build_sh.exists():
        raise FileNotFoundError("build.sh not found")

    content = build_sh.read_text()
    match = re.search(r'APP_VERSION="([^"]+)"', content)
    if not match:
        raise ValueError("APP_VERSION not found in build.sh")

    return match.group(1)


def increment_version(version):
    """Increment patch version (x.y.z -> x.y.z+1)."""
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")

    patch = int(parts[2]) + 1
    return f"{parts[0]}.{parts[1]}.{patch}"


def update_build_sh(new_version):
    """Update version in build.sh."""
    build_sh = Path("build.sh")
    content = build_sh.read_text()
    content = re.sub(r'APP_VERSION="[^"]+"', f'APP_VERSION="{new_version}"', content)
    build_sh.write_text(content)


def update_main_py(new_version):
    """Update version in main.py."""
    main_py = Path("main.py")
    content = main_py.read_text()
    content = re.sub(
        r'version_label = QLabel\("v[^"]+"\)',
        f'version_label = QLabel("v{new_version}")',
        content,
    )
    main_py.write_text(content)


def git_commit_version_change(old_version, new_version):
    """Commit version changes to git."""
    try:
        subprocess.run(
            ["git", "add", "build.sh", "main.py"], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"Version bump: v{old_version} -> v{new_version}"],
            check=True,
            capture_output=True,
        )
        print(f"✅ Git commit created: v{old_version} -> v{new_version}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Git commit failed: {e}")


def main():
    """Main function to increment version."""
    try:
        old_version = get_current_version()
        new_version = increment_version(old_version)

        print(f"🔄 Incrementing version: v{old_version} -> v{new_version}")

        update_build_sh(new_version)
        update_main_py(new_version)

        print(f'✅ Updated build.sh: APP_VERSION="{new_version}"')
        print(f'✅ Updated main.py: version_label = QLabel("v{new_version}")')

        # Auto-commit if git repo
        if Path(".git").exists():
            git_commit_version_change(old_version, new_version)

        return new_version

    except Exception as e:
        print(f"❌ Error incrementing version: {e}")
        return None


if __name__ == "__main__":
    main()
