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

"""Agent-template validator for the Gemini Enterprise Demo Generator.

The A2UI example JSONs and the agent runtime Python live as real files under
agent_template/ (the generated setup script fetches them at run time), so
validation is now direct: parse every example JSON, check the A2UI v0.9
one-press-one-prompt rule the schema cannot express, and byte-compile every
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


def check_one_action_per_prompt(messages):
    """One press must send one prompt. Returns a list of problem strings.

    No schema can catch this: a `MaterialChips` carries a SINGLE `action` for
    ALL of its `options`, so a chip bar built out of one validates perfectly
    and then sends the FIRST chip's `context.prompt` whichever chip the user
    presses. `MaterialChips` is still right for BOUND selection inside a form,
    where the choice travels through `value` and the data model rather than
    through the action, so the rule is specifically "an action, plus more than
    one option".

    Also flags two prompts that are byte-identical within one surface, the
    other way a chip bar silently collapses onto one destination.
    """
    problems = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        body = message.get("updateComponents")
        if not isinstance(body, dict):
            continue
        surface = body.get("surfaceId", "?")
        prompts = {}
        for comp in body.get("components") or []:
            if not isinstance(comp, dict):
                continue
            action = comp.get("action")
            if not isinstance(action, dict):
                continue
            options = comp.get("options")
            if comp.get("component") == "MaterialChips" and isinstance(options, list) and len(options) > 1:
                problems.append(
                    "%s: MaterialChips '%s' has %d options behind ONE action - every "
                    "option would send the same context.prompt. Use one MaterialButton "
                    "per choice, or bind the selection with 'value' and drop the action."
                    % (surface, comp.get("id"), len(options)))
            prompt = ((action.get("event") or {}).get("context") or {}).get("prompt")
            if isinstance(prompt, str):
                if prompt in prompts:
                    problems.append(
                        "%s: '%s' and '%s' both send the prompt %r"
                        % (surface, prompts[prompt], comp.get("id"), prompt))
                prompts[prompt] = comp.get("id")
    return problems


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
                parsed = json.loads(f.read().replace(CURRENCY_PLACEHOLDER, "$"))
        except json.JSONDecodeError as exc:
            failures += 1
            print(f"  ❌ {rel}: {exc}")
            continue
        problems = check_one_action_per_prompt(parsed if isinstance(parsed, list) else [parsed])
        if problems:
            failures += 1
            for problem in problems:
                print(f"  ❌ {rel} {problem}")
            continue
        print(f"  ✅ {rel}")

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
