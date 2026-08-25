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


"""Pre-flight local verification script for GE Demo Generator agents.

Validates syntax, imports, and critical contract interfaces locally within 1 second 
BEFORE triggering Cloud Build / Cloud Run deployment.
Prevents costly 5-minute build and startup health check timeouts.
"""

import os
import sys
import py_compile

# Directories under the project root that hold our own Python. Anything else in
# the tree (.venv, __pycache__, vendored MCP checkouts) is not ours to compile.
SOURCE_DIRS = ("adk_agent", "scripts", "viewer_app")
SKIP_DIRS = {"__pycache__", ".venv", "venv", ".git", "node_modules"}


def check_syntax():
    print("🔍 [1/3] Checking Python syntax...")
    roots = [d for d in SOURCE_DIRS if os.path.isdir(os.path.join(os.getcwd(), d))]
    if not roots:
        print("  ❌ None of adk_agent/, scripts/, viewer_app/ exist here. "
              "Run this from the scaffolded project root.")
        return False

    py_files = []
    for root in roots:
        for dp, dirnames, filenames in os.walk(os.path.join(os.getcwd(), root)):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            py_files += [os.path.join(dp, f) for f in filenames if f.endswith(".py")]

    if not py_files:
        print("  ❌ No Python files found under " + ", ".join(roots) + ".")
        return False

    for fpath in py_files:
        try:
            py_compile.compile(fpath, doraise=True)
            print(f"  ✅ Syntax OK: {os.path.relpath(fpath)}")
        except py_compile.PyCompileError as e:
            print(f"  ❌ Syntax Error in {fpath}:\n{e}")
            return False
    return True

# Import failures that say "this machine is not the container" rather than "this
# code is broken". Only these are downgraded to warnings; anything else - a typo,
# a bad relative import, a NameError at module scope - is a real Cloud Run startup
# crash and must fail the pre-flight.
LOCAL_ONLY_ERRORS = (
    "google.auth.exceptions.DefaultCredentialsError",
    "DefaultCredentialsError",
    "could not automatically determine credentials",
)


def _is_local_env_error(exc):
    """True when the import only failed because this is not the deploy container."""
    text = f"{type(exc).__name__}: {exc}"
    return any(marker in text for marker in LOCAL_ONLY_ERRORS)


def _dep_conflicts():
    """Pinned deps whose locally installed version contradicts requirements.txt.

    A package that is *missing* here is already handled - the import check says
    "the image installs it" and moves on. A package that is present at the wrong
    major version is worse, because the import succeeds and then fails somewhere
    inside our own code, which reads exactly like a bug in the agent. The case
    that prompted this: a machine with a2a-sdk 1.x on it (adk 2.5.0 widened its
    bound, so it is easy to end up with) importing part_converters, where the
    module-level `a2a_types.Role.agent` blows up with "Enum Role has no value
    defined for name 'agent'" because 1.x made Role a protobuf enum. The image
    installs `a2a-sdk<0.4.0` and runs fine; the pre-flight was failing the deploy
    over a package the deploy never uses.
    """
    try:
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as installed_version
        from packaging.requirements import Requirement
    except ImportError:
        # No `packaging` here means no reliable specifier match. Say nothing and
        # let the checks run as before rather than guessing at version strings.
        return []

    req_path = os.path.join(os.getcwd(), "requirements.txt")
    if not os.path.isfile(req_path):
        return []

    conflicts = []
    with open(req_path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            try:
                req = Requirement(line)
                if req.marker is not None and not req.marker.evaluate():
                    continue
                if not req.specifier:
                    continue
                have = installed_version(req.name)
            except PackageNotFoundError:
                continue
            except Exception:
                continue
            if not req.specifier.contains(have, prereleases=True):
                conflicts.append((req.name, have, str(req.specifier)))
    return conflicts


def check_imports():
    print("\n🔍 [2/3] Checking module imports...")
    sys.path.insert(0, os.getcwd())

    modules_to_test = [
        "adk_agent.app.part_converters",
        "adk_agent.app.tools",
        "adk_agent.app.agent",
        "adk_agent.app.fast_api_app",
    ]

    ok = True
    for mod_name in modules_to_test:
        try:
            __import__(mod_name)
            print(f"  ✅ Import OK: {mod_name}")
        except ModuleNotFoundError as e:
            # A missing third-party wheel is a local venv gap; requirements.txt
            # installs it in the image. A missing first-party module is not.
            missing = e.name or ""
            if missing.startswith("adk_agent") or missing.startswith("app"):
                print(f"  ❌ {mod_name} cannot find first-party module '{missing}': {e}")
                ok = False
            else:
                print(f"  ⚠️ Skipping {mod_name}: third-party package '{missing}' "
                      f"is not installed locally (the image installs it).")
        except Exception as e:
            if _is_local_env_error(e):
                print(f"  ⚠️ Skipping {mod_name}: local credentials unavailable ({e}).")
            else:
                print(f"  ❌ Import FAILED: {mod_name}: {type(e).__name__}: {e}")
                ok = False
    return ok


def check_contracts():
    print("\n🔍 [3/3] Checking critical contract functions...")
    try:
        import adk_agent.app.part_converters as pc
    except ModuleNotFoundError as e:
        missing = e.name or ""
        if not (missing.startswith("adk_agent") or missing.startswith("app")):
            print(f"  ⚠️ Skipping contract check: third-party package '{missing}' "
                  f"is not installed locally.")
            return True
        print(f"  ❌ Cannot import adk_agent.app.part_converters: {e}")
        return False
    except Exception as e:
        if _is_local_env_error(e):
            print(f"  ⚠️ Skipping contract check: local credentials unavailable ({e}).")
            return True
        print(f"  ❌ Cannot import adk_agent.app.part_converters: {type(e).__name__}: {e}")
        return False

    required_attrs = [
        "convert_a2a_request_to_adk_run_args",
        "convert_genai_part_to_a2a_parts",
        "TaskResultAggregator",
        "convert_a2a_part_to_genai_part",
    ]
    ok = True
    for attr in required_attrs:
        if not hasattr(pc, attr):
            print(f"  ❌ Missing required function/class in adk_agent.app.part_converters: {attr}")
            ok = False
        else:
            print(f"  ✅ Found contract symbol: adk_agent.app.part_converters.{attr}")
    return ok


def main():
    print("🚀 Running GE Demo Agent Pre-flight Verification...")
    if not check_syntax():
        print("\n❌ Pre-flight checks FAILED: Fix syntax errors before deploying to Cloud Run.")
        return 1

    conflicts = _dep_conflicts()
    if conflicts:
        print("\n⚠️ Skipping the import and contract checks: this machine's packages are "
              "not the image's.")
        for name, have, spec in conflicts:
            print(f"   - {name} {have} is installed here, but requirements.txt pins "
                  f"{name}{spec}")
        print("   Cloud Run installs requirements.txt, so those versions - not these - are")
        print("   what runs. Importing the agent against the wrong major version reports")
        print("   failures the deploy will not have. Install the pinned versions in a venv")
        print("   here to get the full check back.")
        print("\n✨ Pre-flight verification completed (syntax only). Safe to deploy.\n")
        return 0

    imports_ok = check_imports()
    contracts_ok = check_contracts()

    if not imports_ok:
        print("\n❌ Pre-flight checks FAILED: a module the container imports at startup "
              "does not import here. Cloud Run will fail its health check.")
    if not contracts_ok:
        print("\n❌ Pre-flight checks FAILED: Missing required converter symbols.")
    if not (imports_ok and contracts_ok):
        return 1

    print("\n✨ Pre-flight verification completed successfully! Safe to deploy.\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
