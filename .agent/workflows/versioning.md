---
description: Automated versioning workflow for 4Charm
---

# Automated Versioning Workflow

This guide explains how 4Charm manages version numbers using a single source of truth pattern and automatic incrementing.

## Quick Reference

```bash
# Manual version increment (for local builds)
python scripts/increment_version.py           # Increment minor: 5.1.0 → 5.2.0
python scripts/increment_version.py --patch   # Increment patch: 5.1.0 → 5.1.1
python scripts/increment_version.py --set 6.0.0  # Set specific version

# Build with current version
./build.sh
```

## Version Architecture

### Single Source of Truth: `VERSION` File

The [`VERSION`](file:///Users/home/GitHub/4Charm/VERSION) file is the canonical source for the application's version number. All other files are automatically synchronized from this file.

**Files automatically updated:**

- [`src/main.py`](file:///Users/home/GitHub/4Charm/src/main.py) - Docstring and `setApplicationVersion()`
- [`setup.py`](file:///Users/home/GitHub/4Charm/setup.py) - `CFBundleVersion` and `CFBundleShortVersionString`
- [`src/ui/main_window.py`](file:///Users/home/GitHub/4Charm/src/ui/main_window.py) - Version label

## Automatic Versioning (GitHub Actions)

### How It Works

When you push to the `main` branch, a GitHub Action automatically:

1. **Reads** current version from `VERSION` file
2. **Increments** the patch version (5.1.0 → 5.1.1)
3. **Updates** all version references across the codebase
4. **Commits** changes back to the repository with `[skip-version]` tag

### Triggering Auto-Increment

```bash
# Make your changes
git add .
git commit -m "feat: add new feature"
git push origin main

# GitHub Actions will automatically:
# - Increment version 5.1.0 → 5.1.1
# - Update all files
# - Push commit: "chore: bump version to v5.1.1 [skip-version]"
```

### Skipping Auto-Increment

To prevent version increment on a specific push, include `[skip-version]` in your commit message:

```bash
git commit -m "docs: update README [skip-version]"
git push origin main  # Version will NOT be incremented
```

**Auto-skip conditions:**

- Commit message contains `[skip-version]`
- Changes only affect markdown files, LICENSE, or .gitignore
- Commit was made by `github-actions[bot]`

## Manual Versioning (Local Development)

### During Build Process

The [`build.sh`](file:///Users/home/GitHub/4Charm/build.sh) script automatically reads from the `VERSION` file and syncs all files:

```bash
./build.sh  # Uses current VERSION file, syncs all files
```

### Increment Version Manually

Use the [`scripts/increment_version.py`](file:///Users/home/GitHub/4Charm/scripts/increment_version.py) script:

```bash
# Increment minor version (5.1.0 → 5.2.0)
python scripts/increment_version.py

# Increment patch version (5.1.0 → 5.1.1)
python scripts/increment_version.py --patch

# Set specific version
python scripts/increment_version.py --set 6.0.0
```

**Version Format:** `MAJOR.MINOR.PATCH`

**Rollover Logic:**

- Minor version increments reset patch to 0: `5.1.3 → 5.2.0`
- Minor version 9 rolls over to next major: `5.9.0 → 6.0.0`
- Patch increments have no rollover limit: `5.1.9 → 5.1.10 → 5.1.11 ...`

## Version Strategy

| Increment Type | When to Use | Example |
|----------------|-------------|---------|
| **Patch** | Bug fixes, minor tweaks | 5.1.0 → 5.1.1 |
| **Minor** | New features, improvements | 5.1.0 → 5.2.0 |
| **Major** | Breaking changes, major releases | 5.9.0 → 6.0.0 |

**Recommended Workflow:**

- **GitHub Actions** handles patch increments automatically
- **Manually** increment minor version when releasing new features
- **Manually** increment major version for breaking changes

## Implementation Details

### Workflow File

[`.github/workflows/auto-version.yml`](file:///Users/home/GitHub/4Charm/.github/workflows/auto-version.yml)

```yaml
on:
  push:
    branches: [main]
    paths-ignore: ['**.md', 'LICENSE', '.gitignore']

jobs:
  increment-version:
    - Checkout repository
    - Run: python scripts/increment_version.py --patch
    - Commit and push changes
```

### Version Sync Script

[`scripts/increment_version.py`](file:///Users/home/GitHub/4Charm/scripts/increment_version.py)

The script uses regex patterns to find and replace version strings:

```python
# Update src/main.py
content = re.sub(r'Version: [0-9.]+', f'Version: {new_version}', content)
content = re.sub(
    r'app\.setApplicationVersion\("[^"]+"\)',
    f'app.setApplicationVersion("{new_version}")',
    content
)

# Update setup.py
content = re.sub(r'"CFBundleVersion": "[^"]+"', f'"CFBundleVersion": "{new_version}"', content)
```

## Troubleshooting

### Version Mismatch Between Files

If files get out of sync, manually sync them:

```bash
# Read version from VERSION file and sync all files
python scripts/increment_version.py --set $(cat VERSION)
```

### GitHub Action Not Running

Check that:

1. You pushed to the `main` branch
2. Commit message doesn't contain `[skip-version]`
3. Changes include files other than `.md`, `LICENSE`, or `.gitignore`
4. Check GitHub Actions tab for workflow logs

### Infinite Loop Protection

The workflow automatically prevents infinite loops by:

- Adding `[skip-version]` to its own commits
- Skipping when committer is `github-actions[bot]`
- Only triggering on specific file changes

### Manual Version Override

If you need to override the version after an automatic increment:

```bash
# Set to desired version
python scripts/increment_version.py --set 5.5.0

# Commit with skip flag to prevent auto-increment
git add VERSION src/main.py setup.py src/ui/main_window.py
git commit -m "chore: set version to 5.5.0 [skip-version]"
git push origin main
```

## Best Practices

1. **Let GitHub Actions handle patches** - Don't manually increment patch versions
2. **Manually increment minor/major** - Use the script for feature releases
3. **Always sync before building** - `build.sh` handles this automatically
4. **Use `[skip-version]` for docs** - Prevent version bumps for non-code changes
5. **Check version after builds** - Verify all files have matching versions

## Examples

### Example 1: New Feature Release

```bash
# Set to new minor version
python scripts/increment_version.py --set 5.3.0

# Build and test
./build.sh

# Commit and push
git add .
git commit -m "feat: add new download manager [skip-version]"
git push origin main
```

### Example 2: Bug Fix

```bash
# Make your fix
# Let GitHub Actions auto-increment patch version

git add .
git commit -m "fix: resolve crash on invalid URL"
git push origin main

# GitHub Actions will: 5.2.0 → 5.2.1
```

### Example 3: Major Version Update

```bash
# Update to new major version
python scripts/increment_version.py --set 6.0.0

# Build and verify
./build.sh

# Push with skip flag
git add .
git commit -m "release: v6.0.0 with breaking changes [skip-version]"
git push origin main
```
