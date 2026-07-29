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

"""Dependency cap audit for PINNED_DEPS in Code.gs.

The major-cap policy (AGENTS.md section 8) says every pip requirement in
PINNED_DEPS carries an upper bound at the next major. Caps stop an upstream
release from breaking a live demo build, but they are also freezes: without
something that reports them, they rot silently. `a2a-sdk<1.0.0` sat on 0.3.26
while 1.x shipped and nobody noticed.

This script reconstructs the generated requirements.txt (both the plain and the
computer-use variant), resolves each with the pinned uv, and reports:

  MISSING CAP   a requirement has no upper bound        -> policy violation, exit 1
  STALE CAP     a newer major exists above the cap      -> review, smoke deploy
  DRIFT         floor is a major behind what resolves   -> informational
  PYPROJECT     agent_template/pyproject.toml disagrees        -> exit 1

Usage:
    python3 check_deps.py            # audit
    python3 check_deps.py --offline  # skip PyPI, resolve + cap check only
"""

import json
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
CODE_GS = HERE / "app" / "Code.gs"
# The agent template ships a static pyproject.toml that repeats four of the
# PINNED_DEPS requirements; a cap only protects the build if both carry it.
PYPROJECT = HERE / "agent_template" / "pyproject.toml"
# PINNED_DEPS key -> the requirement pyproject.toml must repeat verbatim.
PYPROJECT_KEYS = ("adk", "mcp", "genai", "storage")

# PINNED_DEPS keys that are not pip requirements.
NON_PIP_KEYS = {"pythonImage", "uvImage", "uvVersion", "supergateway"}
# Keys emitted only in the enableComputerUse branch of the requirements heredoc.
COMPUTER_USE_KEYS = {
    "playwright",
    "genaiComputerUse",
    "cuOtelGcpLogging",
    "cuOtelGcpResourceDetector",
}
# Keys that go into the separate viewer_app/requirements.txt, not the agent's.
VIEWER_KEYS = {"viewerFunctionsFramework", "viewerFlask", "viewerFirestore"}

REQ_SPEC = re.compile(
    r"^(?P<name>[A-Za-z0-9._-]+)"
    r"(?P<extras>\[[^\]]*\])?"
    r"(?P<spec>.*)$"
)


def parse_pinned_deps(text):
    """Extract PINNED_DEPS as an ordered list of (key, value) pairs."""
    start = text.index("const PINNED_DEPS = {")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                body = text[start : i + 1]
                break
    else:
        raise SystemExit("check_deps: could not find the end of PINNED_DEPS")

    body = re.sub(r"^\s*//.*$", "", body, flags=re.MULTILINE)
    pairs = re.findall(r"^\s*([A-Za-z][A-Za-z0-9]*)\s*:\s*'([^']*)'", body, re.MULTILINE)
    if not pairs:
        raise SystemExit("check_deps: PINNED_DEPS parsed but no entries found")
    return pairs


def split_spec(value):
    """Return (name, floor, cap, exact) for a pip requirement string."""
    if " @ " in value:  # direct URL / git reference
        return value.split(" @ ", 1)[0].strip(), None, None, False
    match = REQ_SPEC.match(value.strip())
    name = match.group("name")
    spec = match.group("spec")
    floor = None
    cap = None
    exact = False
    for part in spec.split(","):
        part = part.strip()
        if part.startswith(">="):
            floor = part[2:]
        elif part.startswith("=="):
            floor = cap = part[2:]
            exact = True
        elif part.startswith("<="):
            cap = part[2:]
        elif part.startswith("<"):
            cap = part[1:]
    return name, floor, cap, exact


def major(version):
    if not version:
        return None
    head = re.match(r"(\d+)", version)
    return int(head.group(1)) if head else None


def pinned_uv(uv_version):
    """Prefer the uv version the Docker build uses, so resolutions match."""
    candidate = ["uvx", "uv@" + uv_version, "pip", "compile"]
    try:
        probe = subprocess.run(
            ["uvx", "uv@" + uv_version, "--version"],
            capture_output=True, text=True, timeout=180,
        )
        if probe.returncode == 0:
            return candidate, uv_version
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        local = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=60)
        local_v = local.stdout.strip().split()[1] if local.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError, IndexError):
        raise SystemExit("check_deps: uv is not installed (https://docs.astral.sh/uv/)")
    print("  ! uv " + uv_version + " unavailable; falling back to local uv " + local_v)
    print("    Resolutions may differ from the Docker build.")
    return ["uv", "pip", "compile"], local_v


def resolve(requirements, uv_cmd):
    """Run uv pip compile and return {name: version}, or None if it failed."""
    with tempfile.TemporaryDirectory() as tmp:
        req = Path(tmp) / "requirements.txt"
        req.write_text("\n".join(requirements) + "\n", encoding="utf-8")
        out = Path(tmp) / "out.txt"
        proc = subprocess.run(
            uv_cmd + ["--quiet", "--python-version", "3.11", str(req), "-o", str(out)],
            capture_output=True, text=True, timeout=900,
        )
        if proc.returncode != 0:
            return None, proc.stderr.strip()
        resolved = {}
        for line in out.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "==" in line:
                name, _, version = line.partition("==")
                resolved[name.strip().lower()] = version.strip()
        return resolved, None


def pypi_latest(name):
    url = "https://pypi.org/pypi/" + name + "/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.load(response)["info"]["version"]
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError):
        return None


def check_pyproject(values):
    """agent_template/pyproject.toml repeats four PINNED_DEPS requirements.

    The generated requirements.txt is built from PINNED_DEPS, but pyproject.toml
    is a static template file that is copied verbatim into the build context. If
    the two disagree, a cap that looks applied in Code.gs is not actually
    protecting the ADK project install. Fail loudly rather than let them rot.
    """
    if not PYPROJECT.is_file():
        return ["missing " + str(PYPROJECT)]
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r"^dependencies\s*=\s*\[", text, re.MULTILINE)
    if not match:
        return ["could not parse the dependencies list in " + PYPROJECT.name]
    # Scan for the closing bracket by depth: requirement strings contain their
    # own brackets (google-adk[a2a]), so a non-greedy .*?\] stops too early.
    depth = 0
    end = None
    for i in range(match.end() - 1, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end is None:
        return ["unterminated dependencies list in " + PYPROJECT.name]
    declared = set(re.findall(r'"([^"]+)"', text[match.end():end]))
    problems = []
    for key in PYPROJECT_KEYS:
        expected = values.get(key)
        if expected and expected not in declared:
            problems.append(PYPROJECT.name + " is missing " + expected)
    return problems


def main():
    offline = "--offline" in sys.argv
    text = CODE_GS.read_text(encoding="utf-8")
    pairs = parse_pinned_deps(text)
    values = dict(pairs)

    uv_cmd, uv_used = pinned_uv(values.get("uvVersion", "0.11.17"))
    print("Resolving with uv " + uv_used + " (Dockerfile pins " + values.get("uvVersion", "?") + ")")

    agent_keys = [k for k, _ in pairs if k not in NON_PIP_KEYS and k not in VIEWER_KEYS]
    base_keys = [k for k in agent_keys if k not in COMPUTER_USE_KEYS]

    variants = {
        "agent": [values[k] for k in base_keys],
        "agent+computer-use": [values[k] for k in agent_keys],
        "viewer": [values[k] for k in VIEWER_KEYS],
    }

    resolutions = {}
    for label, requirements in variants.items():
        resolved, error = resolve(requirements, uv_cmd)
        if resolved is None:
            print("\n  X " + label + " FAILED to resolve:\n" + (error or "")[:2000])
            return 1
        print("  - " + label + ": " + str(len(resolved)) + " packages resolved")
        resolutions[label] = resolved

    pyproject_problems = check_pyproject(values)

    missing_cap = []
    stale_cap = []
    pin_lag = []
    drift = []

    print("")
    header = "{:<38}{:<14}{:<10}{:<11}{:<11}{}".format(
        "requirement", "floor", "cap", "resolved", "latest", "note"
    )
    print(header)
    print("-" * len(header))

    for key, value in pairs:
        if key in NON_PIP_KEYS:
            continue
        name, floor, cap, exact = split_spec(value)
        if floor is None and cap is None and " @ " in value:
            print("{:<38}{:<14}{:<10}{:<11}{:<11}{}".format(
                name[:37], "(git pin)", "-", "-", "-", "commit-pinned, exempt"))
            continue

        resolved = "-"
        for label, table in resolutions.items():
            if name.lower() in table:
                resolved = table[name.lower()]
                break

        latest = "-" if offline else (pypi_latest(name) or "?")
        notes = []

        if exact:
            # An exact pin is a deliberate choice (matching a reference impl),
            # not a cap. Report how far behind it has fallen, nothing more.
            if latest not in ("-", "?", None) and latest != cap:
                notes.append("exact pin, latest is " + latest)
                pin_lag.append(name + "==" + str(cap) + " vs latest " + latest)
            else:
                notes.append("exact pin")
        elif cap is None:
            notes.append("MISSING CAP")
            missing_cap.append(name)
        elif latest not in ("-", "?", None):
            if major(latest) is not None and major(cap) is not None and major(latest) >= major(cap):
                notes.append("STALE CAP (latest " + latest + " is above the cap)")
                stale_cap.append(name + " cap<" + cap + " vs latest " + latest)

        if resolved != "-" and floor and major(resolved) != major(floor):
            notes.append("floor is major " + str(major(floor)) + ", resolves to " + str(major(resolved)))
            drift.append(name + " floor " + floor + " -> resolved " + resolved)

        print("{:<38}{:<14}{:<10}{:<11}{:<11}{}".format(
            name[:37], floor or "-", cap or "-", resolved, latest, "; ".join(notes)))

    print("")
    if missing_cap:
        print("X POLICY VIOLATION: no upper bound on " + ", ".join(missing_cap))
        print("  Every pip requirement in PINNED_DEPS must cap the next major.")
        print("  See AGENTS.md section 8.")
    if stale_cap:
        print("! STALE CAPS (a cap is now freezing you below a released major):")
        for item in stale_cap:
            print("    " + item)
        print("  Not an error. Evaluate with a full smoke deploy, then")
        print("  either raise the cap or record why it stays.")
    if pin_lag:
        print("i EXACT PINS behind latest (deliberate; upgrade only on purpose):")
        for item in pin_lag:
            print("    " + item)
    if drift:
        print("i FLOOR DRIFT (informational -- the band spans two majors):")
        for item in drift:
            print("    " + item)
    if pyproject_problems:
        print("X DRIFT: agent_template/pyproject.toml disagrees with PINNED_DEPS:")
        for item in pyproject_problems:
            print("    " + item)
        print("  Both files reach the build context; a cap in only one of them")
        print("  does not protect the ADK project install.")
    if not (missing_cap or stale_cap or pin_lag or drift or pyproject_problems):
        print("OK All requirements capped and mirrored, no stale caps, no drift.")

    return 1 if (missing_cap or pyproject_problems) else 0


if __name__ == "__main__":
    sys.exit(main())
