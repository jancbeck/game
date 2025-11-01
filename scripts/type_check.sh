#!/bin/bash
# Type check script for GDScript files
# This script runs Godot in headless mode to parse and validate all scripts

set -e

# Find Godot binary
GODOT_BIN="${GODOT_BIN:-godot}"

# Check if GODOT_BIN is set to a specific path
if [ ! -f "$GODOT_BIN" ]; then
    # Try common locations
    if command -v godot &> /dev/null; then
        GODOT_BIN="godot"
    elif [ -f "/tmp/Godot_v4.5.1-stable_linux.x86_64" ]; then
        GODOT_BIN="/tmp/Godot_v4.5.1-stable_linux.x86_64"
    else
        echo "Error: Godot binary not found."
        echo "Please set GODOT_BIN environment variable or install Godot."
        echo "Example: export GODOT_BIN=/path/to/Godot_v4.5.1-stable_linux.x86_64"
        exit 1
    fi
fi

echo "Using Godot binary: $GODOT_BIN"
echo "Running type check..."

# Run Godot in headless mode to parse scripts
$GODOT_BIN --headless --quit --editor --path .

echo "Type check completed successfully!"
