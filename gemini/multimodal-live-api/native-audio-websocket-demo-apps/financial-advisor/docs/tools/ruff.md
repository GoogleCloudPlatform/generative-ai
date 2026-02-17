# Ruff: Linter and Formatter

This repository uses [Ruff](https://github.com/astral-sh/ruff) as its primary linter and code formatter. Ruff is an extremely fast Python linter and formatter, written in Rust. It aims to be significantly faster than existing tools while integrating seamlessly into your development workflow.

## Why Ruff?

*   **Speed:** Ruff is incredibly fast, often outperforming other linters and formatters by orders of magnitude. This results in minimal overhead during development.
*   **Unified Tooling:** Ruff can replace multiple tools like Flake8, isort, pyupgrade, and more, reducing project dependencies and configuration complexity.
*   **Built-in Formatter:**  Ruff includes a formatter compatible with Black, reducing the need for a separate formatter.
*   **VS Code Integration:** Has a VS Code extension for in-editor linting and formatting.
*   **`pyproject.toml` Configuration:** Ruff supports configuration via `pyproject.toml` for easy project setup.

## Installation

Ruff can be installed using `uv tool`:

```bash
uv tool install ruff
```

## Usage

### Linting

To lint your code, run the following command in your terminal:

```bash
ruff check .
```

This will analyze all Python files in the current directory and its subdirectories.

**Specific Files/Directories:** You can also specify specific files or directories:

```bash
ruff check src/ tests/
ruff check my_file.py
```

### Formatting

To format your code using Ruff's built-in formatter, use:

```bash
ruff format .
```

**Specific Files/Directories:**

```bash
ruff format src/ tests/
ruff format my_file.py
```

### Configuration

Ruff is configured using a `pyproject.toml` file in the root of your project. Here's a sample configuration:

For this repo, the default settings are:
```toml
##############################
#        RUFF SETTINGS       #
##############################
[tool.ruff]
line-length = 120

[tool.ruff.format]
indent-style = "space"
line-ending = "auto"
quote-style = "double"
skip-magic-trailing-comma = false

[tool.ruff.lint.isort]
combine-as-imports = true
lines-between-types = 1
section-order = [
    "first-party",
    "future",
    "local-folder",
    "standard-library",
    "third-party",
]

[tool.ruff.lint.pydocstyle]
convention = "google"
```

For detailed configuration options and the list of available rules, see the [Ruff documentation](https://docs.astral.sh/ruff/).

### VS Code Integration

Ruff has excellent VS Code integration through its official extension.

1. **Install the Ruff extension:** Search for "Ruff" in the VS Code Extensions Marketplace and install it.

With the extension installed, you'll get real-time linting feedback and formatting capabilities directly in your editor.

## Conclusion

Ruff provides a fast, efficient, and convenient way to maintain code quality and consistency in this project. By using it as both a linter and formatter, we minimize dependencies and streamline our development process. Remember to consult the [Ruff documentation](https://docs.astral.sh/ruff/) for more advanced configurations and features.