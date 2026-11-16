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

# Spelling allow file maintenance
SPELLING_ALLOW_FILE=".github/actions/spelling/allow.txt"
SPELLING_EXPECT_FILE=".github/actions/spelling/expect.txt"
if [ -f "$SPELLING_EXPECT_FILE" ]; then
    echo "Combining $SPELLING_EXPECT_FILE into $SPELLING_ALLOW_FILE"
    cat "$SPELLING_EXPECT_FILE" >> "$SPELLING_ALLOW_FILE"
    rm "$SPELLING_EXPECT_FILE"
fi

if [ -f "$SPELLING_ALLOW_FILE" ]; then
    echo "Sorting and de-duplicating $SPELLING_ALLOW_FILE"
    LC_ALL=C sort -u "$SPELLING_ALLOW_FILE" -o "$SPELLING_ALLOW_FILE"
fi

# Determine files to lint
FORMAT_ALL=false
UNSAFE_FLAG=""
LINT_PATHS_NB=()
LINT_PATHS_PY=()

add_file() {
  local f="$1"
  if [[ "$f" == *.ipynb ]]; then
    LINT_PATHS_NB+=("$f")
  elif [[ "$f" == *.py ]] && [[ "${f##*/}" != "noxfile.py" ]]; then
    LINT_PATHS_PY+=("$f")
  fi
}

for arg in "$@"; do
  if [ "$arg" == "--all" ]; then
    FORMAT_ALL=true
  elif [ "$arg" == "--unsafe-fixes" ]; then
    UNSAFE_FLAG="--unsafe-fixes"
  else
    add_file "$arg"
  fi
done

if [ "${#LINT_PATHS_NB[@]}" -eq 0 ] && [ "${#LINT_PATHS_PY[@]}" -eq 0 ]; then
  if [ "$FORMAT_ALL" = true ]; then
    while IFS= read -r f; do
      add_file "$f"
    done < <(find . -not -path "*/.*" \( -name "*.ipynb" -o -name "*.py" \))
  else
    TARGET_BRANCH="main"
    while IFS= read -r f; do
      [ -f "$f" ] && add_file "$f"
    done < <(git diff --name-only --diff-filter=ACMRTUXB "$TARGET_BRANCH" -- '*.ipynb' '*.py')
  fi
fi

if [ "${#LINT_PATHS_NB[@]}" -eq 0 ] && [ "${#LINT_PATHS_PY[@]}" -eq 0 ]; then
  echo "No notebooks or Python files to format."
  exit 0
fi

# Only pull notebook-specific dependencies when notebooks are present
UV_WITH=(--with ruff)
if [ "${#LINT_PATHS_NB[@]}" -gt 0 ]; then
  UV_WITH+=(--with "nbformat>=5.10.4" --with "git+https://github.com/tensorflow/docs")
fi

# Run all formatting steps inside a single uv environment
uv run "${UV_WITH[@]}" bash -s -- "${#LINT_PATHS_NB[@]}" "$UNSAFE_FLAG" "${LINT_PATHS_NB[@]}" "${LINT_PATHS_PY[@]}" << 'EOF'
  set -e
  nb_count=$1
  unsafe_flag=$2
  shift 2

  if [ "$nb_count" -gt 0 ]; then
    echo "Formatting $nb_count notebook(s)..."
    python3 scripts/notebook_processor.py "${@:1:$nb_count}"
  fi

  echo "Running ruff check and format on $# file(s)..."
  ruff check --fix-only ${unsafe_flag:+"$unsafe_flag"} "$@"
  ruff format "$@"

  if [ "$nb_count" -gt 0 ]; then
    python3 -m tensorflow_docs.tools.nbfmt "${@:1:$nb_count}"
  fi
EOF
