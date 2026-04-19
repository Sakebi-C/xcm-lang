#!/bin/bash
# ============================================================
#  XCM Language Engine - Installer
#  Supports: Termux, Linux, macOS
# ============================================================

GITHUB_USER="Sakebi-C"
REPO="xcm-lang"
RAW_URL="https://raw.githubusercontent.com/$GITHUB_USER/$REPO/main/xcm.py"
VERSION_URL="https://raw.githubusercontent.com/$GITHUB_USER/$REPO/main/xcm.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

echo ""
echo -e "${BOLD}============================================${RESET}"
echo -e "${BOLD}       XCM Language Engine Installer       ${RESET}"
echo -e "${BOLD}============================================${RESET}"
echo ""

# Detect platform
if [ -d "/data/data/com.termux" ]; then
    PLATFORM="termux"
    INSTALL_DIR="$PREFIX/bin"
    PYTHON_CMD="python3"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
    INSTALL_DIR="/usr/local/bin"
    PYTHON_CMD="python3"
else
    PLATFORM="linux"
    INSTALL_DIR="/usr/local/bin"
    PYTHON_CMD="python3"
fi

echo -e "  Platform : ${BLUE}$PLATFORM${RESET}"
echo -e "  Install  : ${BLUE}$INSTALL_DIR/xcm${RESET}"
echo ""

# Check Python
echo -e "  ${YELLOW}Checking Python...${RESET}"
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo -e "  ${RED}Python not found!${RESET}"
    if [ "$PLATFORM" == "termux" ]; then
        echo -e "  Run: ${BOLD}pkg install python${RESET}"
    elif [[ "$PLATFORM" == "macos" ]]; then
        echo -e "  Run: ${BOLD}brew install python3${RESET}"
    else
        echo -e "  Run: ${BOLD}sudo apt install python3${RESET}"
    fi
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "  ${GREEN}Found: $PYTHON_VERSION${RESET}"
echo ""

# Check curl or wget
echo -e "  ${YELLOW}Downloading XCM...${RESET}"
if command -v curl &> /dev/null; then
    curl -fsSL "$RAW_URL" -o /tmp/xcm_install.py
elif command -v wget &> /dev/null; then
    wget -q "$RAW_URL" -O /tmp/xcm_install.py
else
    echo -e "  ${RED}curl or wget not found!${RESET}"
    if [ "$PLATFORM" == "termux" ]; then
        echo -e "  Run: ${BOLD}pkg install curl${RESET}"
    fi
    exit 1
fi

# Check download success
if [ ! -f /tmp/xcm_install.py ]; then
    echo -e "  ${RED}Download failed! Check your internet connection.${RESET}"
    exit 1
fi

echo -e "  ${GREEN}Download successful!${RESET}"
echo ""

# Install
echo -e "  ${YELLOW}Installing...${RESET}"
if [ "$PLATFORM" == "termux" ]; then
    cp /tmp/xcm_install.py "$INSTALL_DIR/xcm"
    chmod +x "$INSTALL_DIR/xcm"
else
    sudo cp /tmp/xcm_install.py "$INSTALL_DIR/xcm"
    sudo chmod +x "$INSTALL_DIR/xcm"
fi

# Cleanup
rm -f /tmp/xcm_install.py

# Verify
if command -v xcm &> /dev/null; then
    XCM_VER=$(xcm version 2>&1)
    echo -e "  ${GREEN}Installation successful!${RESET}"
    echo ""
    echo -e "${BOLD}============================================${RESET}"
    echo -e "  $XCM_VER installed!"
    echo -e "  Run: ${BOLD}xcm run <file.xcm>${RESET}"
    echo -e "${BOLD}============================================${RESET}"
    echo ""
else
    echo -e "  ${RED}Installation failed!${RESET}"
    echo -e "  Try manually:"
    echo -e "  ${BOLD}cp /tmp/xcm_install.py $INSTALL_DIR/xcm && chmod +x $INSTALL_DIR/xcm${RESET}"
    exit 1
file