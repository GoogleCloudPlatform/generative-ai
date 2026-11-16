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
LINT_PATHS_GHA=()

add_file() {
  local f="${1#./}"
  if [[ "$f" == *.ipynb ]]; then
    LINT_PATHS_NB+=("$f")
  elif [[ "$f" == *.py ]] && [[ "${f##*/}" != "noxfile.py" ]]; then
    LINT_PATHS_PY+=("$f")
  elif [[ "$f" =~ ^\.github/(workflows/.*|actions/.*/action)\.(yml|yaml)$ ]]; then
    LINT_PATHS_GHA+=("$f")
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

if [ "${#LINT_PATHS_NB[@]}" -eq 0 ] && [ "${#LINT_PATHS_PY[@]}" -eq 0 ] && [ "${#LINT_PATHS_GHA[@]}" -eq 0 ]; then
  if [ "$FORMAT_ALL" = true ]; then
    while IFS= read -r f; do
      add_file "$f"
    done < <(
      find . -not -path "*/.*" \( -name "*.ipynb" -o -name "*.py" \)
      find .github/workflows .github/actions -type f \( -name "*.yml" -o -name "*.yaml" \) 2>/dev/null || true
    )
  else
    TARGET_BRANCH="main"
    while IFS= read -r f; do
      [ -f "$f" ] && add_file "$f"
    done < <(git diff --name-only --diff-filter=ACMRTUXB "$TARGET_BRANCH" -- '*.ipynb' '*.py' '.github/workflows/*.yml' '.github/workflows/*.yaml' '.github/actions/*/action.yml' '.github/actions/*/action.yaml')
  fi
fi

if [ "${#LINT_PATHS_NB[@]}" -eq 0 ] && [ "${#LINT_PATHS_PY[@]}" -eq 0 ] && [ "${#LINT_PATHS_GHA[@]}" -eq 0 ]; then
  echo "No notebooks, Python files, or GitHub Actions files to format."
  exit 0
fi

# Only pull dependencies needed for the detected file types
UV_WITH=()
if [ "${#LINT_PATHS_NB[@]}" -gt 0 ] || [ "${#LINT_PATHS_PY[@]}" -gt 0 ]; then
  UV_WITH+=(--with ruff)
fi
if [ "${#LINT_PATHS_NB[@]}" -gt 0 ]; then
  UV_WITH+=(--with "nbformat>=5.10.4" --with "git+https://github.com/tensorflow/docs")
fi
if [ "${#LINT_PATHS_GHA[@]}" -gt 0 ]; then
  UV_WITH+=(--with zizmor)
fi

# Run all formatting steps inside a single uv environment
uv run "${UV_WITH[@]}" bash -s -- "${#LINT_PATHS_NB[@]}" "${#LINT_PATHS_PY[@]}" "$UNSAFE_FLAG" "${LINT_PATHS_NB[@]}" "${LINT_PATHS_PY[@]}" "${LINT_PATHS_GHA[@]}" << 'EOF'
  set -e
  nb_count=$1
  py_count=$2
  unsafe_flag=$3
  shift 3

  ruff_count=$((nb_count + py_count))
  gha_count=$(($# - ruff_count))

  if [ "$nb_count" -gt 0 ]; then
    echo "Formatting $nb_count notebook(s)..."
    python3 scripts/notebook_processor.py "${@:1:$nb_count}"
  fi

  if [ "$ruff_count" -gt 0 ]; then
    echo "Running ruff check and format on $ruff_count file(s)..."
    ruff check --fix-only ${unsafe_flag:+"$unsafe_flag"} "${@:1:$ruff_count}"
    ruff format "${@:1:$ruff_count}"
  fi

  if [ "$nb_count" -gt 0 ]; then
    python3 -m tensorflow_docs.tools.nbfmt "${@:1:$nb_count}"
  fi

  if [ "$gha_count" -gt 0 ]; then
    zizmor_fix_mode="safe"
    if [ -n "$unsafe_flag" ]; then
      zizmor_fix_mode="all"
    fi
    echo "Running zizmor --fix=$zizmor_fix_mode on $gha_count GitHub Actions file(s)..."
    zizmor --fix="$zizmor_fix_mode" "${@:$((ruff_count + 1))}" || true
  fi
EOF
