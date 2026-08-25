#!/usr/bin/env python3
# Copyright 2026 Google LLC
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

# Deployed as a runtime template into the user's Cloud Shell (not imported by
# repo tooling); validated by py_compile and end-to-end demo deployments.
# Repo-level strict lint/typing is intentionally skipped for this generated-
# origin runtime code; incremental typing is planned as follow-up.
# flake8: noqa
# pylint: skip-file
# mypy: ignore-errors
# ruff: noqa


"""Validates and auto-repairs generated CSV files for BigQuery loading."""

import os
import sys
import csv
import re
from datetime import datetime

def repair_value(val: str) -> str:
    """Cleans up whitespace and standardizes common types."""
    if val is None:
        return ""
    val = val.strip()
    # Normalize ISO dates
    if re.match(r'^\d{4}/\d{1,2}/\d{1,2}$', val):
        parts = val.split('/')
        return f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    return val

def validate_and_repair_csv(filepath: str):
    """Reads a CSV file, repairs formatting, and rewrites clean output."""
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}", file=sys.stderr)
        return False

    print(f"🔍 Validating CSV: {filepath}")
    rows = []
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        for r in reader:
            cleaned_row = [repair_value(cell) for cell in r]
            rows.append(cleaned_row)

    if not rows:
        print(f"❌ Error: CSV is empty ({filepath})", file=sys.stderr)
        return False

    header_len = len(rows[0])
    valid_rows = [rows[0]]
    for i, row in enumerate(rows[1:], start=2):
        if len(row) != header_len:
            print(f"⚠️ Warning: Row {i} length mismatch ({len(row)} vs {header_len}). Adjusting...", file=sys.stderr)
            if len(row) < header_len:
                row += [""] * (header_len - len(row))
            else:
                row = row[:header_len]
        valid_rows.append(row)

    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerows(valid_rows)

    print(f"✅ CSV repaired and validated ({len(valid_rows)-1} rows): {filepath}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate_csv.py <file1.csv> [<file2.csv> ...]")
        sys.exit(1)
    
    success = True
    for fp in sys.argv[1:]:
        if not validate_and_repair_csv(fp):
            success = False
    sys.exit(0 if success else 1)
