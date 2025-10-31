# Test Suite

This directory contains the automated test suite for Gothic Chronicles: The Aftermath.

## Test Structure

```
tests/
├── unit/               # Unit tests - test individual components in isolation
│   ├── test_character_stats.gd
│   ├── test_dialogue_system.gd
│   └── test_thought_cabinet.gd
├── integration/        # Integration tests - test component interactions
│   ├── test_player_interaction.gd
│   └── test_dialogue_integration.gd
├── e2e/               # End-to-end tests - test complete scenarios
│   └── test_game_flow.gd
└── .gutconfig.json    # GUT configuration
```

## Running Tests

### All Tests
```bash
make test
```

### Specific Test Suite
```bash
make test-unit         # Only unit tests
make test-integration  # Only integration tests
make test-e2e         # Only end-to-end tests
```

### Single Test File
```bash
godot --headless --path .. --script ../addons/gut/gut_cmdln.gd -gtest=res://tests/unit/test_character_stats.gd
```

## Writing Tests

All test files must:
- Extend `GutTest`
- Have filename starting with `test_`
- Have test methods starting with `test_`

### Example Test

```gdscript
extends GutTest

var my_component: MyComponent


func before_each():
    # Setup before each test
    my_component = MyComponent.new()
    add_child_autofree(my_component)


func test_something():
    # Arrange
    var input = 5
    
    # Act
    var result = my_component.calculate(input)
    
    # Assert
    assert_eq(result, 10, "Should double the input")


func after_each():
    # Cleanup after each test (usually not needed with add_child_autofree)
    pass
```

## Test Categories

### Unit Tests
- Test single functions/methods
- Mock dependencies
- Fast execution
- High isolation

Example: Testing `CharacterStats.perform_skill_check()`

### Integration Tests
- Test 2-3 components together
- Limited mocking
- Test real interactions
- Medium speed

Example: Testing player interaction with dialogue system

### E2E Tests
- Test complete user scenarios
- No mocking (use real scenes)
- Test from user perspective
- Slower execution

Example: Testing full dialogue conversation flow

## Best Practices

### DO:
✅ Test one thing per test
✅ Use descriptive test names
✅ Follow Arrange-Act-Assert pattern
✅ Clean up resources with `add_child_autofree()`
✅ Use `before_each()` for common setup
✅ Keep tests independent

### DON'T:
❌ Test implementation details
❌ Write tests that depend on other tests
❌ Hardcode specific values when testing ranges
❌ Use `await get_tree().create_timer()` (use `await wait_seconds()`)
❌ Leave failing tests in the codebase

## Common Assertions

```gdscript
# Equality
assert_eq(actual, expected, "message")
assert_ne(actual, not_expected, "message")

# Boolean
assert_true(condition, "message")
assert_false(condition, "message")

# Null
assert_null(value, "message")
assert_not_null(value, "message")

# Numeric
assert_gt(value, minimum, "message")
assert_lt(value, maximum, "message")
assert_between(value, min, max, "message")

# Strings
assert_string_contains(text, substring, "message")
assert_string_starts_with(text, prefix, "message")
assert_string_ends_with(text, suffix, "message")

# Collections
assert_has(collection, item, "message")
assert_does_not_have(collection, item, "message")

# Signals
watch_signals(object)
assert_signal_emitted(object, "signal_name", "message")
assert_signal_not_emitted(object, "signal_name", "message")

# Type
assert_is(object, Type, "message")
```

## Async Testing

For testing asynchronous operations:

```gdscript
func test_async_operation():
    # Start async operation
    my_component.do_something_async()
    
    # Wait for completion
    await wait_seconds(0.1)
    
    # Assert result
    assert_true(my_component.is_done, "Should be done")
```

## Debugging Tests

### Run with verbose output
```bash
godot --headless --path .. --script ../addons/gut/gut_cmdln.gd -gdir=res://tests/unit -glog=2
```

### Run specific test
```bash
godot --headless --path .. --script ../addons/gut/gut_cmdln.gd -gtest=res://tests/unit/test_character_stats.gd
```

### View test logs
```bash
cat gut_log.txt
```

## CI Integration

Tests automatically run on:
- Pull requests
- Pushes to main branch

CI runs:
1. Unit tests
2. Integration tests
3. E2E tests

All must pass before merge.

## Resources

- [GUT Documentation](https://github.com/bitwes/Gut/wiki)
- [TESTING.md](../TESTING.md) - Full testing guide
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
