#!/bin/bash

# Find and clean all Python files in main folder, excluding .venv and other hidden directories
echo "Cleaning Python files..."
find . -name "*.py" -type f -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/.venv/*" | xargs black
find . -name "*.py" -type f -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/.venv/*" | xargs isort

# Find and clean all Jupyter notebook files in main folder, excluding hidden directories
echo "Cleaning Jupyter notebook files..."
find . -name "*.ipynb" -type f -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/.venv/*" | xargs nbqa black
find . -name "*.ipynb" -type f -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/.venv/*" | xargs nbqa isort

# Run nox format session for any remaining files
echo "Running final format check..."
nox -s format