#!/bin/bash
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -e

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv could not be found. Please install it to run the formatting script."
    echo "See https://github.com/astral-sh/uv for installation instructions."
    exit 1
fi

# Define the uv run command with all necessary dependencies
UV_RUN="uv run --with autoflake --with ruff --with nbqa --with nbformat>=5.10.4 --with git+https://github.com/tensorflow/docs"

# Sorting and de-duplicating spelling allow file
SPELLING_ALLOW_FILE=".github/actions/spelling/allow.txt"
if [ -f "$SPELLING_ALLOW_FILE" ]; then
    echo "Sorting and de-duplicating $SPELLING_ALLOW_FILE"
    sort -u "$SPELLING_ALLOW_FILE" -o "$SPELLING_ALLOW_FILE"
fi

# Determine files to lint
FORMAT_ALL=false
UNSAFE_FIXES=false
PASSED_FILES=""
for arg in "$@"; do
  if [ "$arg" == "--all" ]; then
    FORMAT_ALL=true
  elif [ "$arg" == "--unsafe-fixes" ]; then
    UNSAFE_FIXES=true
  elif [[ "$arg" == *.ipynb ]] || [[ "$arg" == *.py ]]; then
    PASSED_FILES="$PASSED_FILES $arg"
  fi
done

LINT_PATHS_NB=""
LINT_PATHS_PY=""

if [ -n "$PASSED_FILES" ]; then
  for f in $PASSED_FILES; do
    if [[ "$f" == *.ipynb ]]; then
      LINT_PATHS_NB="$LINT_PATHS_NB $f"
    elif [[ "$f" == *.py ]]; then
      LINT_PATHS_PY="$LINT_PATHS_PY $f"
    fi
  done
elif [ "$FORMAT_ALL" = true ]; then
  LINT_PATHS_NB=$(find . -name "*.ipynb" -not -path "*/.*")
  LINT_PATHS_PY=$(find . -name "*.py" -not -path "*/.*" -not -name "noxfile.py")
else
  TARGET_BRANCH="main"
  # Get changed files
  CHANGED_FILES=$(git diff --name-only --diff-filter=ACMRTUXB "$TARGET_BRANCH" | sort -u)
  STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACMRTUXB "$TARGET_BRANCH" | sort -u)
  COMMITTED_FILES=$(git diff HEAD "$TARGET_BRANCH" --name-only --diff-filter=ACMRTUXB | sort -u)
  
  ALL_CHANGED=$(echo "$CHANGED_FILES $STAGED_FILES $COMMITTED_FILES" | tr ' ' '\n' | sort -u)
  
  for f in $ALL_CHANGED; do
    if [ -f "$f" ]; then
      if [[ "$f" == *.ipynb ]]; then
        LINT_PATHS_NB="$LINT_PATHS_NB $f"
      elif [[ "$f" == *.py ]] && [ "$f" != "noxfile.py" ]; then
        LINT_PATHS_PY="$LINT_PATHS_PY $f"
      fi
    fi
  done
fi

# --- Format Notebooks ---
if [ -n "$LINT_PATHS_NB" ]; then
  echo "Formatting notebooks..."
  
  # Run custom notebook processor
  $UV_RUN python3 scripts/notebook_processor.py $LINT_PATHS_NB
  
  # Run nbqa tools
  $UV_RUN nbqa autoflake $LINT_PATHS_NB -i -r --remove-all-unused-imports
  
  UNSAFE_FLAG=""
  if [ "$UNSAFE_FIXES" = true ]; then
    UNSAFE_FLAG=" --unsafe-fixes"
  fi
  $UV_RUN nbqa "ruff check --fix-only$UNSAFE_FLAG" $LINT_PATHS_NB
  
  $UV_RUN nbqa "ruff format" $LINT_PATHS_NB
  
  $UV_RUN python3 -m tensorflow_docs.tools.nbfmt $LINT_PATHS_NB
else
  echo "No notebooks to format."
fi

# --- Format Python Files ---
if [ -n "$LINT_PATHS_PY" ]; then
  echo "Formatting Python files..."
  $UV_RUN autoflake -i -r --remove-all-unused-imports $LINT_PATHS_PY
  
  UNSAFE_FLAG=""
  if [ "$UNSAFE_FIXES" = true ]; then
    UNSAFE_FLAG=" --unsafe-fixes"
  fi
  $UV_RUN ruff check --fix-only$UNSAFE_FLAG $LINT_PATHS_PY
  $UV_RUN ruff format $LINT_PATHS_PY
else
  echo "No Python files to format."
fi
