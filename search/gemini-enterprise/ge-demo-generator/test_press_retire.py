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

"""Exercises the v11.90 press-retire helper off-line.

`_pressed_surface_delete_parts()` only ever runs on a live press, and what it
does is destructive by design: it deletes an A2UI surface the user can see. The
two ways it can be wrong are (a) deleting a surface THIS turn is drawing, which
would blank the answer, and (b) firing on a typed message, which has no press to
retire. Both are pure functions of the run arguments and the artifact parts, so
they are tested here instead of in front of an audience.

    python3 test_press_retire.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "agent_template", "adk_agent", "app",
                        "fast_api_app.py")


class _Part:
    """Stands in for an a2a Part carrying one A2UI message."""

    def __init__(self, text=None, msg=None):
        self.text = text
        self.msg = msg


class _Msg:
    def __init__(self, parts):
        self.parts = parts


class _Logger:
    def __init__(self):
        self.lines = []

    def log_text(self, line):
        self.lines.append(line)


def load_helper(logger):
    """Exec the helper out of the template, with the A2UI plumbing stubbed.

    Delimited by name, not by line number, so edits above or below it do not
    silently change what is under test.
    """
    src = open(TEMPLATE, encoding="utf-8").read()
    start = src.index("def _pressed_surface_delete_parts(")
    end = src.index("from adk_agent.app.agent import app as adk_app", start)
    ns = {
        "os": os,
        "json": json,
        "logger": logger,
        "_a2ui_iter_msgs": lambda p: ([p.msg] if getattr(p, "msg", None) else []),
        "_a2ui_surface_id": lambda m: (m.get("updateComponents") or {}).get("surfaceId"),
        "_mk_msg": lambda kind, **body: {"version": "v0.9", kind: body},
        "_build_a2ui_part": lambda m: _Part(msg=m),
    }
    exec(compile(src[start:end], TEMPLATE, "exec"), ns)  # noqa: S102
    return ns["_pressed_surface_delete_parts"]


def press(surface_id, source="chip1"):
    return {"new_message": _Msg([_Part(text=json.dumps({"userAction": {
        "name": "follow_up", "surfaceId": surface_id,
        "sourceComponentId": source, "context": {"prompt": "go"}}}))])}


def rendered(surface_id):
    return _Part(msg={"version": "v0.9", "updateComponents": {
        "surfaceId": surface_id, "components": [{"id": "root"}]}})


def deleted_ids(parts):
    return [p.msg["deleteSurface"]["surfaceId"] for p in parts]


CASES = [
    # name, run arguments, emitted parts, expected deleted surfaceIds
    ("chip press retires its own surface",
     press("suggestions-abc"), [rendered("answer-card")], ["suggestions-abc"]),
    ("gate press retires the action surface",
     press("analysis-plan-actions", "bInline"),
     [rendered("siu-deep-dive"), rendered("suggestions-def")],
     ["analysis-plan-actions"]),
    ("welcome press retires the welcome card",
     press("welcome-card", "b1"), [rendered("intake-overview")], ["welcome-card"]),
    ("a surface this turn re-renders is never deleted",
     press("analysis-plan-actions", "bInline"),
     [rendered("analysis-plan-actions")], []),
    ("typed message retires nothing",
     {"new_message": _Msg([_Part(text="show me the backlog")])}, [], []),
    ("press without a surfaceId retires nothing",
     {"new_message": _Msg([_Part(text=json.dumps(
         {"userAction": {"name": "x", "sourceComponentId": "b1"}}))])}, [], []),
    ("malformed userAction JSON is survived",
     {"new_message": _Msg([_Part(text='{"userAction": {broken')])}, [], []),
    ("no new message at all",
     {}, [], []),
]


def main():
    os.environ.pop("A2UI_KEEP_PRESSED_SURFACE", None)
    logger = _Logger()
    retire = load_helper(logger)
    failures = 0
    print("press-retire (v11.90)")
    for name, run_args, parts, expected in CASES:
        got = deleted_ids(retire(run_args, parts))
        ok = got == expected
        failures += 0 if ok else 1
        print("  %-4s %-52s got=%s" % ("ok" if ok else "FAIL", name, got))

    os.environ["A2UI_KEEP_PRESSED_SURFACE"] = "1"
    got = deleted_ids(retire(press("suggestions-abc"), [rendered("answer-card")]))
    ok = got == []
    failures += 0 if ok else 1
    print("  %-4s %-52s got=%s" % ("ok" if ok else "FAIL",
                                   "kill switch keeps every surface", got))
    os.environ.pop("A2UI_KEEP_PRESSED_SURFACE", None)

    if failures:
        print("\n%d case(s) FAILED" % failures)
        return 1
    print("\nAll %d case(s) passed." % (len(CASES) + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
