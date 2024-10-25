#!/bin/bash
PYTHON_MINOR_VERSION=$(python3 --version | awk -F. '{print $2}')

if [ "$PYTHON_MINOR_VERSION" -gt 12 ]; then
    echo "Python version 3.$PYTHON_MINOR_VERSION detected. Python 3.12 or lower is required for setup to complete."
    echo "If you have multiple versions of Python installed, you can set the correct one by adjusting setup.sh to use a specific version, for example:"
    echo "'python3 -m venv .venv' -> 'python3.12 -m venv .venv'"
    exit 1
fi

if ! command -v cargo &> /dev/null; then
    echo "Cargo (the package manager for Rust) is not present.  This is required for one of this module's dependencies."
    echo "See https://www.rust-lang.org/tools/install for installation instructions."
    exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r dev-requirements.txt
pre-commit install
