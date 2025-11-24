#!/usr/bin/env zsh

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

VENV_DIR=".venv"
PYTHON_EXE="$VENV_DIR/bin/python"

echo -e "${BLUE}🚀 Starting 4Charm Build Process${NC}"

# --- Version Configuration ---
# Read version from VERSION file (single source of truth)
if [[ -f "VERSION" ]]; then
    VERSION=$(cat VERSION)
    echo -e "${YELLOW}📌 Using version from VERSION file: $VERSION${NC}"
else
    echo -e "${YELLOW}⚠️  VERSION file not found, using default: 1.0.0${NC}"
    VERSION="1.0.0"
    echo "$VERSION" > VERSION
fi

# Sync version across all files using increment_version.py
echo -e "${YELLOW}Syncing version across files...${NC}"
"$PYTHON_EXE" scripts/increment_version.py --set "$VERSION" 2>/dev/null || {
    # Fallback to sed if script fails
    echo -e "${YELLOW}⚠️  Using sed fallback for version sync${NC}"
    
    # Update version in src/main.py
    sed -i '' "s/Version: [0-9]*\.[0-9]*\.[0-9]*/Version: $VERSION/" src/main.py 2>/dev/null || true
    sed -i '' "s/app.setApplicationVersion(\"[0-9]*\.[0-9]*\.[0-9]*\")/app.setApplicationVersion(\"$VERSION\")/" src/main.py 2>/dev/null || true
    
    # Update version in setup.py
    sed -i '' "s/\"CFBundleVersion\": \"[0-9]*\.[0-9]*\.[0-9]*\"/\"CFBundleVersion\": \"$VERSION\"/" setup.py 2>/dev/null || true
    sed -i '' "s/\"CFBundleShortVersionString\": \"[0-9]*\.[0-9]*\.[0-9]*\"/\"CFBundleShortVersionString\": \"$VERSION\"/" setup.py 2>/dev/null || true
}

echo -e "${GREEN}✔ Version synchronized: $VERSION${NC}"


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
