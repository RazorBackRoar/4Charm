#!/usr/bin/env zsh

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Use system Python 3.13 directly - no virtual environment
PYTHON_EXE="/opt/homebrew/bin/python3.13"

if [[ ! -x "$PYTHON_EXE" ]]; then
    echo -e "${RED}❌ Python 3.13 not found at $PYTHON_EXE${NC}"
    exit 1
fi

echo -e "${BLUE}🚀 Starting 4Charm Build Process${NC}"
echo -e "${YELLOW}📌 Using Python: $($PYTHON_EXE --version)${NC}"

# --- Version Configuration ---
get_pyproject_version() {
    "$PYTHON_EXE" - <<'PY'
import pathlib, re, sys
pyproject = pathlib.Path('pyproject.toml')
if not pyproject.exists():
    sys.exit('pyproject.toml not found')
match = re.search(r'version\s*=\s*"([^"\n]+)"', pyproject.read_text(encoding='utf-8'))
if not match:
    sys.exit('Unable to locate version in pyproject.toml')
print(match.group(1))
PY
}

VERSION=$(get_pyproject_version)
echo -e "${YELLOW}📌 Version from pyproject.toml: $VERSION${NC}"

# --- Run Build Script ---
echo -e "${BLUE}Running build.py...${NC}"
"$PYTHON_EXE" build.py
