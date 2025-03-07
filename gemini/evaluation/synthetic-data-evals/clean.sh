#!/bin/bash

# Find and clean all Python files
echo "Cleaning Python files..."
find . -name "*.py" -type f | xargs nox -s format --

# Find and clean all Jupyter notebook files
echo "Cleaning Jupyter notebook files..."
find . -name "*.ipynb" -type f | xargs nox -s format --

# Run nox format session for any remaining files
echo "Running final format check..."
nox -s format