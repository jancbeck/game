# Contributing to Gothic Chronicles: The Aftermath

Thank you for your interest in contributing! This guide will help you get started.

## Quick Start

1. **Fork and clone** the repository
2. **Install development tools**: `make install-tools`
3. **Make your changes**
4. **Run checks**: `make check`
5. **Submit a pull request**

## Development Setup

### Prerequisites

- **Godot 4.2+** - [Download here](https://godotengine.org/download)
- **Python 3.12+** - For linting tools
- **Make** - For convenience commands (optional)

### Install Tools

```bash
# Install Python linting tools
make install-tools

# Or manually
pip install gdtoolkit==4.2.2
```

### Pre-commit Hook (Mandatory for Coding Agents)

For coding agents, the pre-commit hook is automatically installed via the `copilot-setup-steps` workflow. This ensures all commits are linted before being pushed.

For manual setup:

```bash
cp .git-hooks/pre-commit.example .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Follow the [GDScript style guide](https://docs.godotengine.org/en/stable/tutorials/scripting/gdscript/gdscript_styleguide.html)
- Write tests for new features
- Update documentation as needed

### 3. Run Checks

```bash
# Format your code
make format

# Check linting
make lint

# Run tests
make test

# Or run everything
make check
```

### 4. Commit Changes

```bash
git add .
git commit -m "Add feature: description of changes"
```

Commit message format:
- **feat:** New feature
- **fix:** Bug fix
- **test:** Add or update tests
- **docs:** Documentation changes
- **refactor:** Code refactoring
- **style:** Formatting changes

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Code Style

### GDScript Guidelines

- Use **static typing** whenever possible
- Follow **snake_case** for variables and functions
- Follow **PascalCase** for classes
- Keep lines under **100 characters**
- Use **tabs for indentation** (Godot default)
- Add **docstrings** for public functions

Example:
```gdscript
class_name MyClass
extends Node

## Brief description of the class
## More details if needed

var health: int = 100
var player_name: String = "Hero"


func calculate_damage(base_damage: int, modifier: float) -> int:
	"""Calculate final damage after applying modifier"""
	return int(base_damage * modifier)
```

### File Organization

```
game/
├── scenes/          # .tscn files
├── scripts/         # .gd files
├── tests/           # Test files
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── addons/          # Third-party addons
```

## Testing

All new features should include tests. See [TESTING.md](TESTING.md) for details.

### Writing Tests

```gdscript
extends GutTest

var my_system: MySystem


func before_each():
	my_system = MySystem.new()
	add_child_autofree(my_system)


func test_something_works():
	var result = my_system.do_something()
	assert_true(result, "Should return true")
```

### Running Tests

```bash
# All tests
make test

# Specific suite
make test-unit
make test-integration
make test-e2e
```

## Pull Request Guidelines

### Before Submitting

- ✅ All tests pass (`make test`)
- ✅ Code is linted (`make lint`)
- ✅ Build validation passes (`make validate-build`)
- ✅ Documentation is updated
- ✅ Commit messages are clear

### PR Description

Include:
1. **What** changes you made
2. **Why** you made them
3. **How** to test them
4. **Screenshots** (if UI changes)

Example:
```markdown
## Description
Add inventory system for managing items

## Changes
- Created Inventory class
- Added UI panel for inventory
- Implemented item pickup interaction
- Added unit tests

## Testing
1. Run the game
2. Walk to an item
3. Press E to pick it up
4. Press I to view inventory

## Screenshots
[Attach screenshot of inventory UI]
```

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests added for new features
- [ ] All tests pass
- [ ] Documentation updated
- [ ] No linting errors
- [ ] Commit messages are descriptive

## Code Review Process

1. **Automated checks** run on your PR (CI)
2. **Manual review** by maintainers
3. **Address feedback** if requested
4. **Merge** when approved

CI must pass before merge:
- ✅ Linting
- ✅ Build validation
- ✅ All tests

## Reporting Issues

When reporting bugs, include:
- **Description** of the issue
- **Steps to reproduce**
- **Expected behavior**
- **Actual behavior**
- **System info** (OS, Godot version)
- **Screenshots** (if applicable)

Use GitHub Issues: [Create an issue](https://github.com/jancbeck/game/issues)

## Feature Requests

Before submitting a feature request:
1. Check if it already exists in issues
2. Consider if it fits the game's vision
3. Provide detailed description and use cases

## Getting Help

- Read [DEVELOPMENT.md](DEVELOPMENT.md) for architecture details
- Read [TESTING.md](TESTING.md) for testing info
- Check [GAMEPLAY.md](GAMEPLAY.md) for game mechanics
- Ask in GitHub Discussions or Issues

## Code of Conduct

- Be respectful and constructive
- Welcome newcomers
- Focus on what's best for the project
- No harassment or discrimination

## Recognition

Contributors will be:
- Listed in project credits
- Mentioned in release notes
- Appreciated for their work! 🎉

## Questions?

Feel free to open an issue or discussion if you have questions!

---

Thank you for contributing! 🎮
