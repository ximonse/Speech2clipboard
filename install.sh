#!/bin/bash
set -e

echo "Speech2Clipboard — Linux installer"
echo "==================================="

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "Error: Python 3 not found. Install it first."
    exit 1
fi

# Install system dependencies
echo ""
echo "Installing system dependencies..."
if command -v apt &>/dev/null; then
    sudo apt install -y python3-tk xclip
elif command -v pacman &>/dev/null; then
    sudo pacman -S --noconfirm tk xclip
elif command -v dnf &>/dev/null; then
    sudo dnf install -y python3-tkinter xclip
else
    echo "Warning: Unknown package manager. Install python3-tk and xclip manually."
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Add user to input group
echo ""
if groups "$USER" | grep -q '\binput\b'; then
    echo "Already in input group — hotkeys should work."
else
    echo "Adding $USER to input group (required for global hotkeys)..."
    sudo usermod -aG input "$USER"
    echo ""
    echo "IMPORTANT: You must log out and back in for hotkeys to work."
fi

echo ""
echo "Done! Run with: python3 skriv-linux.py"
