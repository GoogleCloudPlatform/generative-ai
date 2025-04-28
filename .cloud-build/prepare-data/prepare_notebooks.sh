#!/bin/bash

check_and_comment() {
  local keyword="app.kernel.do_shutdown"

  for filename in /workspace/generative-ai/gemini/getting-started/*.ipynb; do
    if [[ ! -f "$filename" ]]; then
      echo "Error: File not found: $filename" >&2
      continue
    fi

    if grep -q "$keyword" "$filename"; then
      # Keyword found, proceed with commenting it out
      tr '\n' '\r' < "$filename" | sed 's/app.kernel.do_shutdown/#app.kernel.do_shutdown/g' | tr '\r' '\n' > "$filename.tmp"
      mv "$filename.tmp" "$filename"
      echo "Commented out '$keyword' in '$filename'"
    else
      echo "'$keyword' not found in '$filename', skipping..."
    fi
  done
}

check_and_comment