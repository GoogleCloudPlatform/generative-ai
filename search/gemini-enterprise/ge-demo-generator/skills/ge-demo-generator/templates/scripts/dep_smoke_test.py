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


"""Dependency import smoke test, executed during the Docker build.

Walks the generated agent package, collects every third-party module and
symbol the code imports, and resolves each one. When a dependency changes its
module layout under us -- e.g. mcp 2.0.0 removing mcp.shared.session, which
google-adk imports -- the BUILD fails here naming the offending module,
instead of the container dying on import and surfacing only as a Cloud Run
startup probe that retries forever. See AGENTS.md 13.7.

Imports inside a try/except are treated as optional and skipped, so genuinely
optional integrations do not break the build.
"""
import ast
import importlib
import os
import sys

PKG_ROOT = 'adk_agent'
LOCAL_ROOTS = ('adk_agent', 'app')


def collect(path):
    """Return (module, symbol_or_None) pairs for non-optional third-party imports."""
    with open(path, 'r', encoding='utf-8') as handle:
        source = handle.read()
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        # A file we cannot parse is not a dependency problem. Warn and move on:
        # this test must never be the reason a build fails.
        print('  ! skipped ' + path + ' (unparseable: ' + str(exc) + ')')
        return set()

    optional = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for inner in ast.walk(node):
                if isinstance(inner, (ast.Import, ast.ImportFrom)):
                    optional.add(id(inner))

    found = set()
    for node in ast.walk(tree):
        if id(node) in optional:
            continue
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add((alias.name, None))
        elif isinstance(node, ast.ImportFrom):
            # level > 0 is a relative import of our own package
            if node.level or not node.module:
                continue
            for alias in node.names:
                symbol = None if alias.name == '*' else alias.name
                found.add((node.module, symbol))
    return set(p for p in found if p[0].split('.')[0] not in LOCAL_ROOTS)


def resolve(module, symbol):
    obj = importlib.import_module(module)
    if symbol is None or hasattr(obj, symbol):
        return
    # Submodule that has not been imported yet is not an attribute yet.
    importlib.import_module(module + '.' + symbol)


def main():
    if not os.path.isdir(PKG_ROOT):
        print('Dep smoke test SKIPPED: no ' + PKG_ROOT + ' directory')
        return 0

    pairs = set()
    for root, _dirs, files in os.walk(PKG_ROOT):
        for name in files:
            if name.endswith('.py'):
                pairs |= collect(os.path.join(root, name))

    failures = []
    # Sort on (module, symbol or '') -- a plain import yields symbol None and a
    # from-import yields a str, and the default tuple ordering compares the two
    # against each other the moment both forms exist for one module.
    for module, symbol in sorted(pairs, key=lambda pair: (pair[0], pair[1] or '')):
        try:
            resolve(module, symbol)
        except Exception as exc:
            target = module if symbol is None else module + '.' + symbol
            failures.append(target + ' -> ' + type(exc).__name__ + ': ' + str(exc))

    if failures:
        print('FAIL: dependency import smoke test (' + str(len(failures)) + ' broken)')
        for line in failures:
            print('  ' + line)
        print('A dependency changed its module layout. Check PINNED_DEPS caps')
        print('in Code.gs against the installed versions in /app/.dep-versions.')
        return 1

    print('Dep smoke test OK (' + str(len(pairs)) + ' imports resolved)')
    return 0


if __name__ == '__main__':
    sys.exit(main())