#!/bin/bash

# Test runner script based on the GdUnit4 GitHub Action approach
# This runs tests using xvfb-run to provide a virtual display

set -e

# Set GODOT_BIN if not already set
export GODOT_BIN=${GODOT_BIN:-/tmp/Godot_v4.5.1-stable_linux.x86_64}

# Verify Godot binary exists
if [ ! -f "$GODOT_BIN" ]; then
    echo "Error: Godot binary not found at: $GODOT_BIN"
    exit 1
fi

# Import the project if .godot directory doesn't exist
# This is necessary to register GdUnit4 classes
if [ ! -d ".godot" ]; then
    echo "Importing project to register classes..."
    $GODOT_BIN --headless --path . --import --quit 2>&1 | tail -5
    echo "Project import complete."
    echo ""
fi

# Make runtest.sh executable
chmod +x ./addons/gdUnit4/runtest.sh

# Run tests with xvfb-run (virtual X server) similar to the GitHub Action
echo "Running GdUnit4 tests..."
xvfb-run --auto-servernum \
    ./addons/gdUnit4/runtest.sh \
    --audio-driver Dummy \
    --display-driver x11 \
    --rendering-driver opengl3 \
    --single-window \
    --continue \
    --add ./test

exit_code=$?

echo ""
echo "Test run completed with exit code: $exit_code"
exit $exit_code
