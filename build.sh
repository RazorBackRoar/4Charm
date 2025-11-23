#!/usr/bin/env zsh

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

VENV_DIR="build/venv"
PYTHON_EXE="$VENV_DIR/bin/python"

echo -e "${BLUE}🚀 Starting 4Charm Build Process${NC}"

# --- Setup Build Environment ---
echo -e "${YELLOW}Setting up build environment...${NC}"

# Create venv if it doesn't exist
if [[ ! -d "$VENV_DIR" ]]; then
    echo -e "${YELLOW}   Creating virtual environment...${NC}"
    /opt/homebrew/bin/python3.13 -m venv "$VENV_DIR"
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
