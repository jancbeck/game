#!/bin/bash

# Type validation script for GDScript
# Uses Godot's built-in type checking

set -e

echo "Running GDScript type validation..."
echo "===================================="

# Check if godot is available
if ! command -v godot &> /dev/null; then
    echo "Error: Godot not found in PATH"
    echo "Please install Godot 4.2+ or set GODOT environment variable"
    exit 1
fi

# Run Godot with check-only flag to validate types and syntax
# This will catch type errors, undefined variables, etc.
godot --headless --path . --check-only --quit 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Type validation passed!"
    echo "  All scripts have valid types and syntax"
else
    echo ""
    echo "✗ Type validation failed!"
    echo "  Fix the errors above before committing"
    exit 1
fi
