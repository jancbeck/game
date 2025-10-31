.PHONY: help lint format test test-unit test-integration test-e2e validate-build install-tools clean

# Default Godot executable path - override with GODOT_BIN environment variable
GODOT ?= godot
GODOT_HEADLESS ?= godot --headless

help:
	@echo "Gothic Chronicles: The Aftermath - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install-tools     Install development tools (gdlint, gdformat)"
	@echo ""
	@echo "Linting & Formatting:"
	@echo "  make lint             Run GDScript linter on all scripts"
	@echo "  make format           Auto-format all GDScript files"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests (unit + integration + e2e)"
	@echo "  make test-unit        Run only unit tests"
	@echo "  make test-integration Run only integration tests"
	@echo "  make test-e2e         Run only end-to-end tests"
	@echo ""
	@echo "Validation:"
	@echo "  make validate-build   Validate that the project builds correctly"
	@echo "  make check            Run all checks (lint + test + build)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Clean temporary files and logs"

install-tools:
	@echo "Installing GDScript development tools..."
	pip install -q gdtoolkit==4.2.2
	@echo "✓ Tools installed successfully"

lint:
	@echo "Running GDScript linter..."
	@python3 -m gdtoolkit.linter scripts/*.gd
	@echo "✓ Linting complete"

format:
	@echo "Formatting GDScript files..."
	@python3 -m gdtoolkit.formatter scripts/*.gd
	@echo "✓ Formatting complete"

test:
	@echo "Running all tests with GUT..."
	@if command -v $(GODOT) >/dev/null 2>&1; then \
		$(GODOT_HEADLESS) --path . --script addons/gut/gut_cmdln.gd -gconfig=tests/.gutconfig.json; \
	else \
		echo "⚠ Godot not found. Tests require Godot Engine to be installed."; \
		echo "  Please install Godot 4.2+ or set GODOT environment variable."; \
		exit 1; \
	fi

test-unit:
	@echo "Running unit tests..."
	@if command -v $(GODOT) >/dev/null 2>&1; then \
		$(GODOT_HEADLESS) --path . --script addons/gut/gut_cmdln.gd -gdir=res://tests/unit; \
	else \
		echo "⚠ Godot not found. Tests require Godot Engine to be installed."; \
		exit 1; \
	fi

test-integration:
	@echo "Running integration tests..."
	@if command -v $(GODOT) >/dev/null 2>&1; then \
		$(GODOT_HEADLESS) --path . --script addons/gut/gut_cmdln.gd -gdir=res://tests/integration; \
	else \
		echo "⚠ Godot not found. Tests require Godot Engine to be installed."; \
		exit 1; \
	fi

test-e2e:
	@echo "Running end-to-end tests..."
	@if command -v $(GODOT) >/dev/null 2>&1; then \
		$(GODOT_HEADLESS) --path . --script addons/gut/gut_cmdln.gd -gdir=res://tests/e2e; \
	else \
		echo "⚠ Godot not found. Tests require Godot Engine to be installed."; \
		exit 1; \
	fi

validate-build:
	@echo "Validating project build..."
	@if command -v $(GODOT) >/dev/null 2>&1; then \
		$(GODOT_HEADLESS) --path . --check-only --quit 2>&1 | grep -i error && exit 1 || echo "✓ Build validation passed"; \
	else \
		echo "⚠ Godot not found. Build validation requires Godot Engine."; \
		exit 1; \
	fi

check: lint validate-build test
	@echo ""
	@echo "========================================="
	@echo "✓ All checks passed!"
	@echo "========================================="

clean:
	@echo "Cleaning temporary files..."
	@rm -f tests/gut_log.txt
	@rm -rf .godot/exported/
	@rm -rf .godot/imported/
	@echo "✓ Cleanup complete"
