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

"""Agent-template validator for the GE Demo Generator.

The A2UI example JSONs and the agent runtime Python live as real files under
agent_template/ (the generated setup script fetches them at run time), so
validation is now direct: parse every example JSON and byte-compile every
Python file. Run from this directory:

    python3 validate_examples.py
"""

import glob
import json
import os
import py_compile
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(ROOT, "agent_template")
# Placeholder substituted by the setup script with the per-demo currency symbol.
CURRENCY_PLACEHOLDER = "[CURRENCY]"


def main() -> int:
    failures = 0

    examples = sorted(glob.glob(os.path.join(TEMPLATE, "adk_agent", "app", "examples", "*", "*.json")))
    if not examples:
        print("❌ No example JSONs found under agent_template/")
        return 1
    for path in examples:
        rel = os.path.relpath(path, ROOT)
        try:
            with open(path, encoding="utf-8") as f:
                json.loads(f.read().replace(CURRENCY_PLACEHOLDER, "$"))
            print(f"  ✅ {rel}")
        except json.JSONDecodeError as exc:
            failures += 1
            print(f"  ❌ {rel}: {exc}")

    py_files = sorted(glob.glob(os.path.join(TEMPLATE, "**", "*.py"), recursive=True))
    for path in py_files:
        rel = os.path.relpath(path, ROOT)
        try:
            py_compile.compile(path, doraise=True)
            print(f"  ✅ {rel}")
        except py_compile.PyCompileError as exc:
            failures += 1
            print(f"  ❌ {rel}: {exc}")

    total = len(examples) + len(py_files)
    if failures:
        print(f"\n❌ {failures}/{total} file(s) failed validation.")
        return 1
    print(f"\n✅ All {total} template files validated ({len(examples)} JSON, {len(py_files)} Python).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
