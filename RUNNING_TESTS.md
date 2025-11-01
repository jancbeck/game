# Running Unit Tests

This document explains how to run the GdUnit4 tests for this project.

## Prerequisites

- Godot 4.5.1 or later
- GdUnit4 addon installed in `addons/gdUnit4/`
- A display server (X11) or virtual display (xvfb) for headless environments

## Running Tests Locally

### Step 1: Import the Project

First, import the project to register GdUnit4 classes:

```bash
export GODOT_BIN=/path/to/godot
$GODOT_BIN --path ./ -e --headless --quit-after 2000
```

### Step 2: Run the Tests

```bash
chmod +x ./addons/gdUnit4/runtest.sh
./addons/gdUnit4/runtest.sh --add ./test
```

**Note**: In headless environments (like CI), you need a virtual display. Use `xvfb-run`:

```bash
xvfb-run --auto-servernum ./addons/gdUnit4/runtest.sh --add ./test
```

## Test Suites

The project contains 24 unit tests across 2 test suites:

- **CharacterStatsTest** (10 tests) - Tests for character statistics system
- **DialogueSystemIntegrationTest** (14 tests) - Integration tests for dialogue system

## Expected Output

Successful test run:
```
Overall Summary: 24 test cases | 0 errors | 0 failures | 0 flaky | 0 skipped | 0 orphans |
Exit code: 0
```

## CI Environment

The GitHub Actions workflow handles both steps automatically:
1. Restores the Godot project cache (imports project)
2. Runs tests using the GdUnit4 action with xvfb-run
