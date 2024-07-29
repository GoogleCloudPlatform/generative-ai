#!/bin/bash
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script automatically formats and lints all notebooks that have changed from the head of the main branch.
#
# Options:
# -t: Test-mode. Only test if format and linting are required but make no changes to files.
#
# Returns:
# This script will return 0 if linting was successful/unneeded and 1 if there were any errors.

# `+e` enables the script to continue even when a command fails
set +e

# `-o pipefail` sets the exit code to the rightmost comment to exit with a non-zero
set -o pipefail

# Use RTN to return a non-zero value if the test fails.
RTN="0"

is_test=false

# Process all options supplied on the command line
while getopts 'tc' arg; do
    case $arg in
    't')
        is_test=true
        ;;
    *)
        echo "Unimplemented flag"
        exit 1
        ;;
    esac
done

echo "Test mode: $is_test"

# Read in user-provided notebooks
notebooks=()
for arg in "$@"; do
    if [[ $arg == *.ipynb ]]; then
        notebooks+=("$arg")
    fi
done

# Only check notebooks in test folders modified in this pull request.
# Note: Use process substitution to persist the data in the array
if [ ${#notebooks[@]} -eq 0 ]; then
    echo "Checking for changed notebooks using git"
    while read -r file || [ -n "$line" ]; do
        notebooks+=("$file")
    done < <(git diff --name-only main... | grep '\.ipynb$')
fi

problematic_notebooks=()
if [ ${#notebooks[@]} -gt 0 ]; then
    for notebook in "${notebooks[@]}"; do
        if [ -f "$notebook" ]; then
            echo "Checking notebook: ${notebook}"

            NBFMT_RTN="0"
            BLACK_RTN="0"
            PYUPGRADE_RTN="0"
            ISORT_RTN="0"
            FLAKE8_RTN="0"

            if [ "$is_test" = true ]; then
                echo "Running nbfmt..."
                python3 -m tensorflow_docs.tools.nbfmt --test "$notebook"
                NBFMT_RTN=$?
                # echo "Running black..."
                # python3 -m nbqa black "$notebook" --check
                # BLACK_RTN=$?
                echo "Running pyupgrade..."
                python3 -m nbqa pyupgrade --exit-zero-even-if-changed "$notebook"
                PYUPGRADE_RTN=$?
                echo "Running isort..."
                python3 -m nbqa isort "$notebook" --check
                ISORT_RTN=$?
                echo "Running flake8..."
                python3 -m nbqa flake8 "$notebook" --show-source --extend-ignore=W391,E501,F821,E402,F404,W503,E203,E722,W293,W291
                FLAKE8_RTN=$?
            else
                echo "Running black..."
                python3 -m nbqa black "$notebook"
                BLACK_RTN=$?
                echo "Running pyupgrade..."
                python3 -m nbqa pyupgrade --exit-zero-even-if-changed "$notebook"
                PYUPGRADE_RTN=$?
                echo "Running isort..."
                python3 -m nbqa isort "$notebook"
                ISORT_RTN=$?
                echo "Running nbfmt..."
                python3 -m tensorflow_docs.tools.nbfmt "$notebook"
                NBFMT_RTN=$?
                echo "Running flake8..."
                python3 -m nbqa flake8 "$notebook" --show-source --extend-ignore=W391,E501,F821,E402,F404,W503,E203,E722,W293,W291
                FLAKE8_RTN=$?
            fi

            NOTEBOOK_RTN="0"

            if [ "$NBFMT_RTN" != "0" ]; then
                NOTEBOOK_RTN="$NBFMT_RTN"
                printf "nbfmt: Failed\n"
            fi

            if [ "$BLACK_RTN" != "0" ]; then
                NOTEBOOK_RTN="$BLACK_RTN"
                printf "black: Failed\n"
            fi

            if [ "$PYUPGRADE_RTN" != "0" ]; then
                NOTEBOOK_RTN="$PYUPGRADE_RTN"
                printf "pyupgrade: Failed\n"
            fi

            if [ "$ISORT_RTN" != "0" ]; then
                NOTEBOOK_RTN="$ISORT_RTN"
                printf "isort: Failed\n"
            fi

            if [ "$FLAKE8_RTN" != "0" ]; then
                NOTEBOOK_RTN="$FLAKE8_RTN"
                printf "flake8: Failed\n"
            fi

            echo "Notebook lint finished with return code = $NOTEBOOK_RTN"
            echo ""
            if [ "$NOTEBOOK_RTN" != "0" ]; then
                problematic_notebooks+=("$notebook")
                RTN=$NOTEBOOK_RTN
            fi
        fi
    done
else
    echo "No notebooks modified in this pull request."
fi

echo "All tests finished. Exiting with return code = $RTN"

if [ ${#problematic_notebooks[@]} -gt 0 ]; then
    echo "The following notebooks could not be automatically linted:"
    printf '%s\n' "${problematic_notebooks[@]}"
fi

exit "$RTN"
