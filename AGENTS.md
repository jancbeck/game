# Copilot Instructions for Gothic 2 spiritual successor

## Repository Overview

**Tech:** Godot 4.5.1 (Forward+), GDScript (typed), GDScript Toolkit 4.x, Git LFS for assets.

```bash
# Format - lint
source .venv/bin/activate
gdformat scripts/ &- gdlint scripts/

# Import - generate UIDs
/Applications/Godot.app/Contents/MacOS/Godot --path . -e --headless --quit-after 2000

# Run tests using gdUnit4 (smoke tests for fast iteration)
/Applications/Godot.app/Contents/MacOS/Godot --headless -s res://addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a res://test
```
