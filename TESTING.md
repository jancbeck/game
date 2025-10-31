# Testing and Validation Guide

This document explains how to use the testing, linting, and validation infrastructure for Gothic Chronicles: The Aftermath.

## Table of Contents

- [Quick Start](#quick-start)
- [Development Tools](#development-tools)
- [Linting](#linting)
- [Testing](#testing)
- [Build Validation](#build-validation)
- [Continuous Integration](#continuous-integration)
- [Writing Tests](#writing-tests)

## Quick Start

### For Coding Agents

The development environment is automatically set up via the `copilot-setup-steps` workflow. This includes:
- Python 3.12 with gdtoolkit
- Godot 4.2.2
- Mandatory pre-commit hook for automatic linting

### Install Development Tools (Manual)

```bash
make install-tools
```

This installs:
- `gdlint` - GDScript linter
- `gdformat` - GDScript code formatter

**Note**: The pre-commit hook is mandatory and automatically installed by the setup workflow.

### Run All Checks

```bash
make check
```

This runs:
1. Linting on all GDScript files
2. Build validation
3. All tests (unit, integration, and E2E)

## Development Tools

### Requirements

- **Python 3.12+** - For linting tools
- **Godot 4.2+** - For running tests and build validation
- **Make** - For convenient commands (optional)

### Installation

```bash
# Install Python tools
pip install gdtoolkit==4.2.2

# Or use Make
make install-tools
```

## Linting

### What is Linting?

Linting checks your code for style issues, potential bugs, and adherence to best practices.

### Run Linter

```bash
# Check all scripts (recommended)
make lint

# Or manually using Python module
python -m gdtoolkit.linter scripts/*.gd
```

### Auto-Format Code

```bash
# Format all scripts automatically (recommended)
make format

# Or manually using Python module
python -m gdtoolkit.formatter scripts/*.gd
```

### Linting Rules

See `.gdlintrc` for configuration. Key rules:
- Max line length: 100 characters
- Max function length: 50 lines
- Proper class/function naming conventions
- No trailing whitespace
- Correct definition order

## Testing

We use **GUT (Godot Unit Testing)** framework for all tests.

### Test Structure

```
tests/
├── unit/               # Unit tests (individual components)
│   ├── test_character_stats.gd
│   ├── test_dialogue_system.gd
│   └── test_thought_cabinet.gd
├── integration/        # Integration tests (component interactions)
│   ├── test_player_interaction.gd
│   └── test_dialogue_integration.gd
├── e2e/               # End-to-end tests (complete scenarios)
│   └── test_game_flow.gd
└── .gutconfig.json    # GUT configuration
```

### Run All Tests

```bash
make test
```

### Run Specific Test Suites

```bash
# Unit tests only
make test-unit

# Integration tests only
make test-integration

# E2E tests only
make test-e2e
```

### Manual Test Execution

```bash
# Run all tests
godot --headless --path . --script addons/gut/gut_cmdln.gd -gconfig=tests/.gutconfig.json

# Run specific directory
godot --headless --path . --script addons/gut/gut_cmdln.gd -gdir=res://tests/unit
```

### Test Output

Test results are displayed in the console and logged to `tests/gut_log.txt`.

Example output:
```
======================
All Tests
======================
* test_character_stats.gd
  - test_initial_attributes: PASSED
  - test_perform_skill_check: PASSED
  ...

Tests:    45 passed
Asserts:  156 of 156 passed
```

## Build Validation

Validates that the Godot project can load and compile correctly.

```bash
make validate-build

# Or manually
godot --headless --path . --check-only --quit
```

This checks:
- Scene files are valid
- Scripts have no parse errors
- Resources load correctly
- No circular dependencies

## Continuous Integration

### GitHub Actions Workflow

When you create a PR, GitHub Actions automatically:

1. **Lints** all GDScript files
2. **Validates** the project build
3. **Runs** unit tests
4. **Runs** integration tests
5. **Runs** E2E tests

See `.github/workflows/ci.yml` for details.

### PR Requirements

For a PR to be merged:
- ✅ All linting checks must pass
- ✅ Build validation must succeed
- ✅ All tests must pass

### Viewing CI Results

1. Go to your PR on GitHub
2. Scroll to "Checks" section
3. Click on any failed check to see details
4. Download test artifacts for detailed logs

## Writing Tests

### Unit Test Example

```gdscript
extends GutTest

var my_component: MyComponent

func before_each():
    my_component = MyComponent.new()
    add_child_autofree(my_component)

func test_something():
    my_component.do_something()
    assert_true(my_component.did_it, "Should have done it")

func test_with_value():
    var result = my_component.calculate(5)
    assert_eq(result, 10, "Should double the value")
```

### Common Assertions

```gdscript
# Equality
assert_eq(actual, expected, "message")
assert_ne(actual, not_expected, "message")

# Boolean
assert_true(value, "message")
assert_false(value, "message")

# Null checks
assert_null(value, "message")
assert_not_null(value, "message")

# Numeric comparisons
assert_gt(value, min, "message")  # greater than
assert_lt(value, max, "message")  # less than
assert_between(value, min, max, "message")

# Strings
assert_string_contains(text, substring, "message")

# Signals
watch_signals(object)
assert_signal_emitted(object, "signal_name", "message")

# Objects
assert_has(dict, key, "message")
assert_is(object, ClassName, "message")
```

### Integration Test Tips

- Test interactions between 2-3 components
- Use `add_child_autofree()` for automatic cleanup
- Test realistic scenarios
- Use `await wait_seconds(0.1)` for async operations

### E2E Test Tips

- Test complete user workflows
- Load actual game scenes
- Test from user's perspective
- Use `await wait_frames(2)` for scene initialization

### Test Naming

- Prefix all test files with `test_`
- Name test methods clearly: `test_what_it_does()`
- Group related tests in same file

## Troubleshooting

### "Godot not found"

Ensure Godot is installed and in your PATH:

```bash
# Set GODOT environment variable
export GODOT=/path/to/godot

# Or add to PATH
export PATH=$PATH:/path/to/godot
```

### Tests Fail Locally But Pass in CI

- Check Godot version (must be 4.2+)
- Ensure all dependencies are committed
- Check for platform-specific issues

### Linting Errors

Run `make format` to auto-fix most issues, then fix remaining issues manually.

### Import Errors in Tests

Ensure you're using the correct resource paths:
```gdscript
# Correct
var scene = load("res://scenes/player.tscn")

# Incorrect
var scene = load("scenes/player.tscn")
```

## Best Practices

### Do:
✅ Write tests for all new features
✅ Run `make check` before pushing
✅ Fix linting errors immediately
✅ Keep tests fast and focused
✅ Use meaningful test names
✅ Clean up test resources

### Don't:
❌ Commit without running tests
❌ Disable linting rules without good reason
❌ Write tests that depend on timing
❌ Skip CI checks
❌ Leave commented-out test code

## Additional Resources

- [GUT Documentation](https://github.com/bitwes/Gut/wiki)
- [GDScript Style Guide](https://docs.godotengine.org/en/stable/tutorials/scripting/gdscript/gdscript_styleguide.html)
- [Godot Testing Best Practices](https://docs.godotengine.org/en/stable/tutorials/scripting/debug/index.html)

## Getting Help

If you encounter issues:
1. Check this documentation
2. Look at existing tests for examples
3. Review CI logs for error details
4. Ask in team chat or create an issue
