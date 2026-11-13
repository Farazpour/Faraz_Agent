#!/bin/bash
# Agent Faraz - Installer for macOS & Linux

set -e

echo ""
echo "███████╗ █████╗ ██████╗  █████╗ ███████╗     █████╗  ██████╗ ███████╗███╗   ██╗████████╗"
echo "██╔════╝██╔══██╗██╔══██╗██╔══██╗╚══███╔╝    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝"
echo "█████╗  ███████║██████╔╝███████║  ███╔╝     ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   "
echo "██╔══╝  ██╔══██║██╔══██╗██╔══██║ ███╔╝      ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   "
echo "██║     ██║  ██║██║  ██║██║  ██║███████╗    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   "
echo "╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   "
echo ""
echo "══════════════════════════════════════════════════════════════════════════════════════════"
echo "                 Autonomous Terminal AI Agent  |  macOS & Linux Installer V1.0.0"
echo "══════════════════════════════════════════════════════════════════════════════════════════"
echo ""

# Find Python 3
PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "[ERROR] Python 3.10+ is required but not found."
    echo "Please install Python from https://www.python.org or via brew/apt."
    exit 1
fi

echo "[OK] Found Python: $($PYTHON_BIN --version)"
echo ""

echo "[>>] Installing Agent Faraz package and dependencies..."
$PYTHON_BIN -m pip install -e . --quiet

echo ""
echo "[OK] Installation completed successfully!"
echo ""
echo "══════════════════════════════════════════════════════════════════════════════════════════"
echo " Agent Faraz is ready! Run it from any directory using:"
echo ""
echo "     faraz"
echo ""
echo " Or execute a single-shot mission:"
echo ""
echo "     faraz \"Explain this project architecture\""
echo "══════════════════════════════════════════════════════════════════════════════════════════"
echo ""
