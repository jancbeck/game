#!/bin/bash
set -e

# Run Godot to generate .uid files
godot --path . -e --headless --quit-after 2000

# Check if any files were modified
if ! git diff --exit-code --quiet; then
    echo "❌ Error: Godot import generated new or modified files."
    echo ""
    echo "Modified files:"
    git diff --name-only
    echo ""
    echo "Please run the following command and commit the changes:"
    echo "  godot --path . -e --headless --quit-after 2000"
    echo ""
    exit 1
fi

echo "✅ All Godot import files are up to date"
