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

"""Local A2UI Examples Schema Validator for GE Demo Generator.

Extracts all embedded A2UI examples from Code.gs, simulates GAS template
literal evaluation, and validates them against the official A2UI schema
before deployment.
"""

import re
import json
import sys
import codecs

try:
    from a2ui.schema.manager import A2uiSchemaManager
    from a2ui.basic_catalog.provider import BasicCatalog
except ImportError:
    print("❌ Error: 'a2ui' package is not installed. Please run inside your '.venv' virtual environment.")
    sys.exit(1)

def main():
    # Initialize official A2UI 0.8 Schema Manager
    try:
        catalog_config = BasicCatalog.get_config(version='0.8', examples_path='.')
        manager = A2uiSchemaManager(version='0.8', catalogs=[catalog_config])
        catalog = manager.get_selected_catalog()
    except Exception as e:
        print(f"❌ Failed to initialize A2UI Schema Manager: {e}")
        sys.exit(1)

    # Read Code.gs
    try:
        with open('app/Code.gs', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ Error: app/Code.gs not found in the current working directory.")
        sys.exit(1)

    # Regex to extract embedded example JSON heredocs inside Code.gs
    heredoc_re = re.compile(
        r"cat\s+<<'(__[A-Z0-9_]+__)'\s+>\s+adk_agent/app/examples/0\.8/(.*?\.json)\n(.*?)\n\1",
        re.DOTALL
    )
    matches = heredoc_re.findall(content)

    print(f"Found {len(matches)} A2UI examples embedded in Code.gs\n")
    failed = False

    for delim, filename, json_text in matches:
        print(f"Validating {filename} (Delimiter: {delim})...")
        try:
            # Simulate JS template literal evaluation by escaping backslash sequences.
            # This correctly converts double '\\n' to '\n' characters and parses correctly.
            simulated_js_text = codecs.escape_decode(bytes(json_text, "utf-8"))[0].decode("utf-8")
            
            # Validate example against strict A2UI JSON schema
            catalog._validate_example(filename, simulated_js_text)
            print(f"  ✅ {filename} is VALID!")
        except json.JSONDecodeError as jde:
            print(f"  ❌ {filename} failed JSON parse: {jde}")
            print("  --- Raw Text snippet (around error) ---")
            print(json_text[:500])
            print("  ---------------------------------------")
            failed = True
        except ValueError as ve:
            print(f"  ❌ {filename} failed A2UI schema validation:\n     {ve}")
            failed = True
        except Exception as e:
            print(f"  ❌ {filename} failed with unexpected validation error: {e}")
            failed = True

    print("=" * 60)
    if failed:
        print("❌ Validation FAILED! Please fix the syntax/schema issues in Code.gs before deploying.")
        sys.exit(1)
    else:
        print("🎉 All embedded A2UI examples validated successfully! Safe to deploy.")
        sys.exit(0)

if __name__ == '__main__':
    main()
