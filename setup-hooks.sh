#!/bin/bash
#
# Setup script to configure git hooks for this repository

echo "Configuring git to use .githooks directory..."
git config core.hooksPath .githooks

echo "Making hooks executable..."
chmod +x .githooks/*

echo ""
echo "✓ Git hooks configured successfully!"
echo ""
echo "The following hooks are now active:"
ls -1 .githooks/
echo ""
echo "Note: Make sure 'eza' is installed on your system."
echo "Install with: sudo apt install eza (Ubuntu/Debian) or brew install eza (macOS)"
