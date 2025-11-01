# GdUnit4 Testing Setup Notes

## Issue Discovered

When running GdUnit4 v6.0.1 tests locally via command line with Godot 4.5.1, the following error occurs:

```
SCRIPT ERROR: Parse Error: Could not find type "GdUnitTestCIRunner" in the current scope.
          at: GDScript::reload (res://addons/gdUnit4/bin/GdUnitCmdTool.gd:5)
```

## Root Cause

When Godot runs scripts directly using `godot --headless -s script.gd`, it does **not** initialize plugins from the `[editor_plugins]` section of `project.godot`. This means:

1. GdUnit4's internal classes (like `GdUnitTestCIRunner`, `CmdOption`, `GdUnitResult`, etc.) are not loaded
2. The test runner script `GdUnitCmdTool.gd` fails to parse because it references these unavailable types
3. Tests cannot run via the command-line `runtest.sh` script

## Why CI Works

The GitHub Action `MikeSchulze/gdUnit4-action@v1.2.2` works because it:
- Handles GdUnit4 installation automatically
- Has special initialization logic that properly loads the plugin before running tests
- Uses Godot's project import system correctly

## Local Testing Workaround

For local development, use the **Godot Editor** to run tests:

1. Install GdUnit4 v6.0.1+ via Godot Asset Library
2. Open the project in Godot Editor (4.5.1+)
3. Open the GdUnit4 inspector panel (bottom dock)
4. Click "Run All Tests" or select individual test suites

## Setup for Copilot Environment

The `copilot-setup-steps.yml` now includes:
- Godot 4.5.1 installation
- GdUnit4 v6.0.1 installation
- Plugin enablement in project.godot

However, **command-line test execution** will still fail due to the plugin initialization issue described above. The CI workflow uses the GitHub Action which handles this correctly.

## Test Files

- `test/CharacterStatsTest.gd` - 10 unit tests for CharacterStats class
- `test/DialogueSystemIntegrationTest.gd` - 13 integration tests using Scene Runner

## Recommendations

1. For CI: Continue using `MikeSchulze/gdUnit4-action@v1.2.2` (working correctly)
2. For local dev: Use Godot Editor's GdUnit4 inspector panel
3. Don't rely on `addons/gdUnit4/runtest.sh` for local testing with this GdUnit4 version

## Environment Setup Commands

```bash
# Download Godot 4.5.1
wget https://github.com/godotengine/godot/releases/download/4.5.1-stable/Godot_v4.5.1-stable_linux.x86_64.zip
unzip Godot_v4.5.1-stable_linux.x86_64.zip
chmod +x Godot_v4.5.1-stable_linux.x86_64

# Download GdUnit4 v6.0.1
mkdir -p addons && cd addons
wget https://github.com/MikeSchulze/gdUnit4/archive/refs/tags/v6.0.1.zip
unzip v6.0.1.zip
mv gdUnit4-6.0.1/addons/gdUnit4 .
rm -rf gdUnit4-6.0.1 v6.0.1.zip
```
