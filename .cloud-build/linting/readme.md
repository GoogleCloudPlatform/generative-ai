# Notebook Linter Script

This Python script automates the linting process for Jupyter Notebook files (`.ipynb`) within a specified directory. It utilizes `nbqa`, `pylint`, and `flake8-nb` to enforce code quality and style guidelines.

## Purpose

The script aims to:

- Install necessary linting tools (`nbqa`, `flake8-nb`, `pylint`).
- Iterate through all `.ipynb` files in the `/workspace/generative-ai/gemini/getting-started` directory.
- Run `pylint` and `flake8-nb` on each notebook to identify potential code issues and style violations.
- Provide error messages for any linting failures.

## Usage

1. **Save the script:** Save the provided Python script as `lint_notebooks.py`.
2. **Ensure Python Environment:** Make sure you have pull down a python container in your cloud-build file.
3. **Add script to pipeline:**
