# Screenshot System Documentation

## Overview

The Screenshot System provides functionality to capture screenshots of the game viewport, which is useful for:
- Visual feedback during development
- Code iteration and debugging
- Documentation and testing
- AI agent interaction (allowing agents to see game state)

## Usage

### Keyboard Shortcut

Press **F12** at any time during gameplay to take a screenshot. The screenshot will be saved in the `screenshots/` folder at the project root.

### Programmatic API

You can also take screenshots programmatically from any script:

```gdscript
# Get the screenshot manager
var screenshot_manager = get_tree().get_first_node_in_group("screenshot_manager")

# Take a screenshot with auto-generated filename
var filepath = screenshot_manager.take_screenshot()

# Take a screenshot with custom name
var filepath = screenshot_manager.take_screenshot("my_screenshot")

# Take a screenshot after waiting for frames to render
var filepath = await screenshot_manager.take_screenshot_delayed(2, "delayed_screenshot")
```

### Signal

The ScreenshotManager emits a signal when a screenshot is taken:

```gdscript
screenshot_manager.screenshot_taken.connect(func(filepath: String):
	print("Screenshot saved to: ", filepath)
)
```

## Configuration

The ScreenshotManager can be configured through export variables in the Godot editor:

- **screenshots_folder**: Folder where screenshots are saved (default: "screenshots")
- **screenshot_key**: Key to trigger screenshot (default: KEY_F12)
- **enable_keyboard_shortcut**: Enable/disable keyboard shortcut (default: true)

## Screenshot Location

Screenshots are saved to:
- **Relative path**: `res://screenshots/`
- **Absolute path**: Displayed in console output when screenshot is taken

The folder is automatically created on first use and is excluded from git via `.gitignore`.

### Example Screenshot

An example screenshot showing the main game scene is included for reference:
- `screenshots/example_screenshot.png` - Demonstrates the visual feedback system

## Filename Format

Screenshots are automatically named with timestamps:
```
screenshot_YYYY-MM-DD_HH-MM-SS_NNN.png
```

For example:
```
screenshot_2025-11-01_14-30-45_001.png
```

Custom names can also be provided:
```
my_screenshot.png
```

## Implementation Details

The screenshot system uses Godot's viewport texture capture:
```gdscript
var image = get_viewport().get_texture().get_image()
image.save_png(filepath)
```

## Limitations

- Screenshots only work when a rendering context is available (not in headless mode)
- Screenshots capture the entire viewport content
- File format is PNG only (best quality for game screenshots)

## Testing

The screenshot system includes comprehensive tests:
- **Unit tests**: Test filename generation, counter increments, configuration
- **Integration tests**: Test actual screenshot capture (with headless mode handling)

Run tests with:
```bash
godot --headless -s res://addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a res://test
```

## For AI Agents

This system allows AI agents to:
1. Take screenshots programmatically via the API
2. View the rendered game state visually
3. Iterate on UI and visual changes with immediate feedback
4. Document their work with visual evidence

Example agent usage:
```gdscript
# After making changes to the UI
var screenshot_manager = get_tree().get_first_node_in_group("screenshot_manager")
var path = screenshot_manager.take_screenshot("after_ui_changes")
print("Visual feedback available at: ", ProjectSettings.globalize_path("res://" + path))
```
