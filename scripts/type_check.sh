#!/bin/bash
# Type check script for GDScript files
# This script runs Godot in headless mode to parse and validate all scripts

set -e

# Find Godot binary
if [ -n "$GODOT_BIN" ]; then
    # GODOT_BIN is explicitly set, validate it exists as file or command
    if [ -f "$GODOT_BIN" ]; then
        # Valid file path
        echo "Using Godot binary: $GODOT_BIN"
    elif command -v "$GODOT_BIN" &> /dev/null; then
        # Valid command in PATH
        echo "Using Godot binary: $GODOT_BIN"
    else
        echo "Error: GODOT_BIN is set to '$GODOT_BIN' but it doesn't exist or is not executable."
        exit 1
    fi
elif command -v godot &> /dev/null; then
    # godot is in PATH
    GODOT_BIN="godot"
    echo "Using Godot binary: $GODOT_BIN"
else
    echo "Error: Godot binary not found."
    echo "Please set GODOT_BIN environment variable or install Godot in PATH."
    echo "Example: export GODOT_BIN=/path/to/Godot_v4.5.1-stable_linux.x86_64"
    exit 1
fi

echo "Running type check..."

# Run Godot in headless mode to parse scripts
"$GODOT_BIN" --headless --quit --editor --path .

echo "Type check completed successfully!"
