#!/usr/bin/env zsh

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

VENV_DIR=".venv"

find_python() {
    local candidates=("/opt/homebrew/bin/python3.13" "$(command -v python3 2>/dev/null)" "/usr/bin/python3")
    for candidate in "${candidates[@]}"; do
        if [[ -n "$candidate" && -x "$candidate" ]]; then
            echo "$candidate"
            return 0
        fi
    done
    echo "❌ Python3 interpreter not found" >&2
    exit 1
}

PYTHON_BIN="$(find_python)"
PYTHON_EXE="$VENV_DIR/bin/python"

echo -e "${BLUE}🚀 Starting 4Charm Build Process${NC}"

# --- Version Configuration ---
get_pyproject_version() {
    "$PYTHON_BIN" - <<'PY'
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
echo -e "${YELLOW}📌 Using version from pyproject.toml: $VERSION${NC}"


# --- Setup Build Environment ---
echo -e "${YELLOW}Setting up build environment...${NC}"

# Create venv if it doesn't exist
if [[ ! -d "$VENV_DIR" ]]; then
    echo -e "${YELLOW}   Creating virtual environment...${NC}"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# Install dependencies
echo -e "${YELLOW}   Installing dependencies...${NC}"
"$PYTHON_EXE" -m pip install --upgrade pip >/dev/null
"$PYTHON_EXE" -m pip install -r requirements.txt >/dev/null
"$PYTHON_EXE" -m pip install py2app >/dev/null

echo -e "${GREEN}✔ Build environment ready${NC}"

# --- Run Build Script ---
echo -e "${BLUE}Running build.py...${NC}"
"$PYTHON_EXE" build.py
