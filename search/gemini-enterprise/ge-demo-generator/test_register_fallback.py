#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Exercises the Gemini Enterprise registration fallback off-line (v11.91).

Two guards decide whether a deploy ends with a working agent, and both of them
only ever run against a live Discovery Engine:

  1. the authorization read-back, which clears AUTH_ID when the resource is not
     readable - naming one that does not exist makes the registration fail with
     404 NOT_FOUND and costs the demo its agent AND its direct chat link;
  2. register_ge_agent_with_fallback, which retries without the authorization
     when the authorized attempt produces no agent.

Both are pure shell, so they are tested here with a stubbed curl and a stubbed
register_agent.py instead of in front of an audience. The blocks are sliced out
of Code.gs by name, so edits above or below them do not change what is tested.

    python3 test_register_fallback.py
"""

import os
import subprocess
import sys

SAMPLE = os.path.dirname(os.path.abspath(__file__))
CODE_GS = os.path.join(SAMPLE, "app", "Code.gs")

# The bytes in Code.gs are not the bytes the generated script receives: both
# blocks live inside a JS template literal, so `\$` is a dollar sign and a
# backslash before a newline is a line continuation JS removes. Resolve the
# same escapes the runtime would (see section 2 of AGENTS.md).
_JS_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "\\": "\\",
    "`": "`",
    "$": "$",
    '"': '"',
    "'": "'",
    "\n": "",  # line continuation
}


def unescape(src: str) -> str:
    """Resolve the JS escapes in text taken from inside a template literal."""
    out = []
    i = 0
    while i < len(src):
        if src[i] == "\\" and i + 1 < len(src):
            out.append(_JS_ESCAPES.get(src[i + 1], src[i + 1]))
            i += 2
            continue
        out.append(src[i])
        i += 1
    return "".join(out)


def slice_block(src: str, start_marker: str, end_marker: str) -> str:
    """The bash between two markers, as the generated script receives it."""
    start = src.index(start_marker)
    end = src.index(end_marker, start) + len(end_marker)
    block = src[start:end]
    # Neither block interpolates today. If one ever does, the naive unescape
    # above would silently test the wrong bytes, so refuse instead.
    if "${" in block:
        raise SystemExit(
            "%r now contains a ${...} interpolation - teach this test to "
            "resolve it before trusting the result." % start_marker
        )
    return unescape(block)


def run_bash(script: str) -> subprocess.CompletedProcess:
    """Run under `set -e`, the way the generated setup script runs."""
    return subprocess.run(
        ["bash", "-e"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )


# --- 1. the authorization read-back gate -------------------------------------
GATE_PRELUDE = """
TOKEN=stub-token
PROJECT_ID=stub-project
AUTH_ID=demo-acme-x7k2-auth
curl() { echo "$FAKE_HTTP"; }
"""

GATE_CASES = [
    # name, HTTP code curl reports, AUTH_ID afterwards
    ("readable authorization is used", "200", "demo-acme-x7k2-auth"),
    ("404 clears it, the agent still registers", "404", ""),
    ("403 clears it", "403", ""),
    ("unreachable API clears it", "000", ""),
]


# --- 2. the registration fallback --------------------------------------------
FALLBACK_PRELUDE = """
# Replaces the real one, which shells out to register_agent.py.
register_ge_agent() {
  case "$MODE" in
    always)     echo "AGENT_ID:agents/aaa" ;;
    auth_fails) if [ -z "$3" ]; then echo "AGENT_ID:agents/bbb"
                else echo "Error registering agent (404): NOT_FOUND"; return 1; fi ;;
    never)      echo "Error registering agent (500)"; return 1 ;;
  esac
}
"""

FALLBACK_CASES = [
    # name, stub mode, authorization id, agent id, retried, degraded warning
    ("authorized attempt succeeds", "always", "demo-auth", "agents/aaa", False, False),
    ("authorization refused, retry wins", "auth_fails", "demo-auth", "agents/bbb", True, True),
    ("both attempts fail", "never", "demo-auth", "", True, False),
    ("no authorization, succeeds", "always", "", "agents/aaa", False, False),
    ("no authorization, fails - no pointless retry", "never", "", "", False, False),
]


def main() -> int:
    """Run both case sets and report."""
    with open(CODE_GS, encoding="utf-8") as handle:
        src = handle.read()
    gate = slice_block(src, "AUTH_GET=\\$(curl", '  AUTH_ID=""\nfi')
    fallback = slice_block(src, "  register_ge_agent_with_fallback() {", "\n  }\n")

    failures = 0
    print("authorization read-back gate")
    for name, http, expected in GATE_CASES:
        out = run_bash(
            'FAKE_HTTP=%s\n%s\n%s\necho "AUTH_ID=[$AUTH_ID]"\n'
            % (http, GATE_PRELUDE, gate)
        )
        got = out.stdout.strip().splitlines()[-1]
        ok = got == "AUTH_ID=[%s]" % expected and out.returncode == 0
        failures += 0 if ok else 1
        print("  %-4s %-44s %s" % ("ok" if ok else "FAIL", name, got))

    print("\nregistration fallback")
    for name, mode, auth, agent, retried, degraded in FALLBACK_CASES:
        out = run_bash(
            "MODE=%s\n%s\n%s\nregister_ge_agent_with_fallback global app1 '%s'\n"
            'echo "AGENT_ID=[$AGENT_ID]"\n' % (mode, FALLBACK_PRELUDE, fallback, auth)
        )
        text = out.stdout
        got_agent = text.strip().splitlines()[-1]
        got_retried = "retrying without it" in text
        got_degraded = "WITHOUT end-user OAuth" in text
        ok = (
            got_agent == "AGENT_ID=[%s]" % agent
            and got_retried == retried
            and got_degraded == degraded
            and out.returncode == 0
        )
        failures += 0 if ok else 1
        print(
            "  %-4s %-44s %s retried=%s degraded=%s"
            % ("ok" if ok else "FAIL", name, got_agent, got_retried, got_degraded)
        )

    total = len(GATE_CASES) + len(FALLBACK_CASES)
    if failures:
        print("\n%d of %d case(s) FAILED" % (failures, total))
        return 1
    print("\nAll %d case(s) passed." % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
