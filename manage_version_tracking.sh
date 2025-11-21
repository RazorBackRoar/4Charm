#!/usr/bin/env zsh
# Helper script to manage version file git tracking

case "$1" in
  hide)
    echo "🔒 Hiding version file changes from git/IDE..."
    git update-index --skip-worktree build.sh main.py setup.py
    echo "✅ Version files hidden (changes won't show in IDE)"
    ;;
  show)
    echo "🔓 Showing version file changes in git/IDE..."
    git update-index --no-skip-worktree build.sh main.py setup.py
    echo "✅ Version files visible (changes will show in IDE)"
    ;;
  status)
    echo "📋 Checking which files are hidden:"
    git ls-files -v | grep "^S" | cut -c 3-
    ;;
  *)
    echo "Usage: $0 {hide|show|status}"
    echo ""
    echo "  hide   - Hide version file changes from IDE (auto-increment won't show)"
    echo "  show   - Show version file changes in IDE (when you want to commit)"
    echo "  status - Check which files are currently hidden"
    exit 1
    ;;
esac
