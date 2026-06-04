#!/usr/bin/env bash
# ONI - Orbital Network Infrastructure
# One-click installer for GitHub
# Usage: curl -fsSL https://raw.githubusercontent.com/technicdev/ONI/main/install.sh | bash
# Or:   bash <(curl -fsSL https://raw.githubusercontent.com/technicdev/ONI/main/install.sh)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "  ___  _   _ ___ "
echo " / _ \| \ | |_ _|"
echo "| | | |  \| || | "
echo "| |_| | |\  || | "
echo " \___/|_| \_|___|"
echo ""
echo -e "${BLUE}Orbital Network Infrastructure${NC}"
echo -e "${YELLOW}One-Click Installer v1.0${NC}"
echo ""

# --- Detect OS ---
OS="$(uname -s)"
ARCH="$(uname -m)"
echo -e "${BLUE}[*]${NC} Detected: ${OS} ${ARCH}"

# --- Parse arguments ---
INSTALL_DIR="${ONI_DIR:-$HOME/ONI}"
INSTALL_BROWSER=true
INSTALL_MANAGER=true
INSTALL_DEVKIT=true
BROWSER_ONLY=false
MANAGER_ONLY=false
CLONE_REPO=true
REPO_URL="https://github.com/technicdev/ONI.git"
BRANCH="main"

usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --dir PATH           Install directory (default: ~/ONI)"
    echo "  --browser-only       Only install the Orbit Browser"
    echo "  --manager-only       Only install the ONI Manager"
    echo "  --no-devkit          Skip ONI DevKit installation"
    echo "  --no-clone           Don't clone repo (run from local copy)"
    echo "  --help               Show this help"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir) INSTALL_DIR="$2"; shift 2 ;;
        --browser-only) BROWSER_ONLY=true; INSTALL_MANAGER=false; INSTALL_DEVKIT=false ;;
        --manager-only) MANAGER_ONLY=true; INSTALL_BROWSER=false; INSTALL_DEVKIT=false ;;
        --no-devkit) INSTALL_DEVKIT=false ;;
        --no-clone) CLONE_REPO=false ;;
        --help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# --- Check Python ---
echo -e "${BLUE}[1/6]${NC} Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}Error: Python 3 is required but not found.${NC}"
    echo "Install Python 3.8+ from https://www.python.org/downloads/"
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
echo -e "  ${GREEN}✓${NC} Python ${PY_VERSION} found"

# --- Create directories ---
echo -e "${BLUE}[2/6]${NC} Setting up directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/apps"
mkdir -p "$INSTALL_DIR/data"
mkdir -p "$INSTALL_DIR/data/cache"
mkdir -p "$INSTALL_DIR/data/domains"
mkdir -p "$INSTALL_DIR/data/peers"
mkdir -p "$INSTALL_DIR/data/logs"
echo -e "  ${GREEN}✓${NC} Directories created at ${INSTALL_DIR}"

# --- Clone or copy ONI ---
if [ "$CLONE_REPO" = true ]; then
    echo -e "${BLUE}[3/6]${NC} Downloading ONI..."
    if command -v git &> /dev/null; then
        if [ -d "$INSTALL_DIR/.git" ]; then
            echo -e "  ${YELLOW}•${NC} Updating existing installation..."
            cd "$INSTALL_DIR" && git pull origin $BRANCH 2>/dev/null || true
        else
            git clone --depth 1 --branch $BRANCH "$REPO_URL" "$INSTALL_DIR/tmp_oni" 2>/dev/null || {
                echo -e "  ${YELLOW}⚠ Git clone failed, downloading ZIP instead...${NC}"
                curl -fsSL "https://github.com/technicdev/ONI/archive/refs/heads/$BRANCH.zip" -o /tmp/oni.zip
                unzip -qo /tmp/oni.zip -d /tmp/oni_extract
                cp -r /tmp/oni_extract/*/* "$INSTALL_DIR/" 2>/dev/null || true
                rm -rf /tmp/oni.zip /tmp/oni_extract
            }
            if [ -d "$INSTALL_DIR/tmp_oni" ]; then
                cp -r "$INSTALL_DIR/tmp_oni/"* "$INSTALL_DIR/" 2>/dev/null || true
                rm -rf "$INSTALL_DIR/tmp_oni"
            fi
        fi
    else
        echo -e "  ${YELLOW}⚠ Git not found, downloading ZIP...${NC}"
        curl -fsSL "https://github.com/technicdev/ONI/archive/refs/heads/$BRANCH.zip" -o /tmp/oni.zip
        unzip -qo /tmp/oni.zip -d /tmp/oni_extract
        cp -r /tmp/oni_extract/*/* "$INSTALL_DIR/" 2>/dev/null || true
        rm -rf /tmp/oni.zip /tmp/oni_extract
    fi
    echo -e "  ${GREEN}✓${NC} ONI downloaded"
else
    echo -e "  ${YELLOW}•${NC} Using local files (--no-clone)"
fi

# --- Install Python dependencies ---
echo -e "${BLUE}[4/6]${NC} Installing dependencies..."
DEPS=("websockets" "flask" "requests" "aiohttp")
for dep in "${DEPS[@]}"; do
    echo -e "  Installing ${YELLOW}${dep}${NC}..."
    $PYTHON -m pip install "$dep" -q 2>/dev/null || $PYTHON -m pip install "$dep" --user -q 2>/dev/null || true
done

# Install tkinter if missing
if $PYTHON -c "import tkinter" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} tkinter available"
else
    echo -e "  ${YELLOW}⚠ tkinter not found. GUI apps may not work.${NC}"
    echo "  Install: sudo apt install python3-tk (Linux) or brew install python-tk (Mac)"
fi

echo -e "  ${GREEN}✓${NC} Dependencies installed"

# --- Create desktop entries (Linux) ---
if [ "$(uname)" = "Linux" ]; then
    echo -e "${BLUE}[5/6]${NC} Creating desktop applications..."
    mkdir -p "$HOME/.local/share/applications"
    mkdir -p "$HOME/.local/share/icons"

    # ONI Manager icon
    cat > "$HOME/.local/share/icons/oni-manager.png" 2>/dev/null << 'ICONEOF'
# This is a placeholder - the app will use its own icon
ICONEOF

    # Create .desktop for ONI Manager
    cat > "$HOME/.local/share/applications/oni-manager.desktop" << EOF
[Desktop Entry]
Name=ONI Manager
Comment=Manage your ONI network nodes and domains
Exec=$PYTHON $INSTALL_DIR/apps/oni_manager.py
Icon=$INSTALL_DIR/apps/oni-manager-icon.png
Terminal=false
Type=Application
Categories=Network;Utility;
Keywords=oni;orbit;network;p2p;
StartupWMClass=ONIManager
EOF

    # Create .desktop for Orbit Browser
    cat > "$HOME/.local/share/applications/orbit-browser.desktop" << EOF
[Desktop Entry]
Name=Orbit Browser
Comment=Browse the ONI decentralized web
Exec=$PYTHON $INSTALL_DIR/apps/orbit_browser_app.py
Icon=$INSTALL_DIR/apps/orbit-browser-icon.png
Terminal=false
Type=Application
Categories=Network;WebBrowser;
Keywords=oni;orbit;browser;web;
StartupWMClass=OrbitBrowser
EOF

    # Make them executable
    chmod +x "$HOME/.local/share/applications/oni-manager.desktop"
    chmod +x "$HOME/.local/share/applications/orbit-browser.desktop"

    # Update desktop database
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

    echo -e "  ${GREEN}✓${NC} Desktop apps created"
    echo -e "  ${YELLOW}  → Find 'ONI Manager' and 'Orbit Browser' in your app menu${NC}"
elif [ "$(uname)" = "Darwin" ]; then
    echo -e "${BLUE}[5/6]${NC} Creating macOS applications..."
    echo -e "  ${YELLOW}  → macOS app bundles not auto-generated${NC}"
    echo -e "  ${YELLOW}  → Run apps manually: cd $INSTALL_DIR/apps && $PYTHON oni_manager.py${NC}"
fi

# --- Final setup ---
echo -e "${BLUE}[6/6]${NC} Finalizing..."

# Create symlinks for easy CLI access
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/oni" << 'EOF'
#!/bin/bash
# ONI CLI shortcut
INSTALL_DIR="${ONI_DIR:-$HOME/ONI}"
PYTHON=$(command -v python3 || command -v python)
case "$1" in
    start)       shift; $PYTHON "$INSTALL_DIR/start_oni.py" "$@" ;;
    node)        shift; $PYTHON "$INSTALL_DIR/p2p/oni_node.py" "$@" ;;
    ons)         shift; $PYTHON "$INSTALL_DIR/ons/ons_server.py" "$@" ;;
    registrar)   shift; $PYTHON "$INSTALL_DIR/orbit-registrar/registrar.py" "$@" ;;
    browser)     shift; $PYTHON "$INSTALL_DIR/apps/orbit_browser_app.py" "$@" ;;
    manager)     shift; $PYTHON "$INSTALL_DIR/apps/oni_manager.py" "$@" ;;
    devkit)      cd "$INSTALL_DIR/ONI_DevKit" && $PYTHON -m http.server 9091 --bind 127.0.0.1 ;;
    help|--help|-h)
        echo "ONI CLI - Orbital Network Infrastructure"
        echo ""
        echo "Usage: oni <command> [options]"
        echo ""
        echo "Commands:"
        echo "  start       Start all ONI components"
        echo "  node        Start an ONI P2P node"
        echo "  ons         Start the ONS server"
        echo "  registrar   Start the domain registrar"
        echo "  browser     Launch the Orbit Browser"
        echo "  manager     Launch the ONI Manager"
        echo "  devkit      Open the ONI Developer Kit docs"
        ;;
    *)           echo "Usage: oni <command> (start|node|ons|registrar|browser|manager|devkit)" ;;
esac
EOF
chmod +x "$HOME/.local/bin/oni"

# Add to PATH if not already
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc" 2>/dev/null || true
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc" 2>/dev/null || true
    echo -e "  ${YELLOW}  → Added ~/.local/bin to PATH${NC}"
fi

# Save install info
cat > "$INSTALL_DIR/.oni_install_info" << EOF
INSTALL_DATE="$(date -Iseconds)"
INSTALL_VERSION="1.0.0"
INSTALL_PYTHON="$PYTHON"
INSTALL_PYTHON_VERSION="$PY_VERSION"
INSTALL_OS="$OS"
INSTALL_ARCH="$ARCH"
EOF

echo ""
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ ONI Installation Complete!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}📁${NC} Installed at:    ${INSTALL_DIR}"
echo ""
echo -e "  ${CYAN}🚀${NC} Quick Start:"
echo -e "      ${YELLOW}oni start${NC}        - Launch all ONI components"
echo -e "      ${YELLOW}oni browser${NC}      - Launch Orbit Browser"
echo -e "      ${YELLOW}oni manager${NC}      - Launch ONI Manager"
echo -e "      ${YELLOW}oni devkit${NC}       - Open Developer Kit"
echo ""
echo -e "  ${CYAN}🖥️${NC} Desktop Apps (Linux):"
echo -e "      ${YELLOW}Orbit Browser${NC}    - Find in your app menu"
echo -e "      ${YELLOW}ONI Manager${NC}      - Find in your app menu"
echo ""
echo -e "  ${CYAN}📖${NC} Documentation:"
echo -e "      ${YELLOW}$INSTALL_DIR/ONI_DevKit/index.html${NC}"
echo ""
echo -e "  ${GREEN}═══ ONI: The People's Internet ═══${NC}"
echo ""