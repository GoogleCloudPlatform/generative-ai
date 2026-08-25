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

"""Exercises the v11.92 surfaceId-anchor persistence off-line.

The cross-turn rescope guard is the only thing standing between a second card of
the same type and GE patching the FIRST one in place, and it decides from a dict
that used to live in process memory alone. That made it wrong exactly where it
could not be noticed: a scale-to-zero wiped the anchors while the GE client kept
every card on screen, so the next turn re-used an id GE had already bound to an
older message and the card silently never rendered (confirmed 2026-08-25 on a
live demo - the third analysis-plan card of a session, first request after an
idle shutdown, no [surface_rescope] line, text-only turn).

Reproducing that in front of an audience costs an instance recycle mid-demo, so
the recycle is simulated here instead: the registry is cleared between turns and
the snapshot has to carry the anchors across. Read from the same agent_template/
file the running demo is built from, the way test_press_retire.py is.

    python3 test_surface_registry_persist.py
"""
import ast
import contextvars
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "agent_template", "adk_agent", "app",
                        "fast_api_app.py")

# Everything the guard touches, pulled by name so edits elsewhere in the file
# cannot change what is under test.
UNDER_TEST = (
    "_get_surface_registry", "_snapshot_surface_registry", "_load_surface_registry",
    "_rescope_one", "_rescope_reused_surfaces", "_a2ui_body", "_a2ui_kind",
    "_mk_msg", "_a2ui_components", "_a2ui_is_full_card_tree", "_a2ui_catalog_id",
)


class _Logger:
    def __init__(self):
        self.lines = []

    def log_text(self, line):
        self.lines.append(line)


def load_helpers(logger):
    src = open(TEMPLATE, encoding="utf-8").read()
    wanted = set(UNDER_TEST)
    bodies = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted:
            bodies.append(ast.unparse(node))
            wanted.discard(node.name)
    if wanted:
        raise SystemExit("not in the template any more: %s" % ", ".join(sorted(wanted)))
    ns = {
        "re": re, "json": json, "contextvars": contextvars, "logger": logger,
        "_session_surface_registry": {},
        "_current_surface_guard": contextvars.ContextVar("surface_guard", default=None),
        "_A2UI_MSG_KEYS": ("createSurface", "updateComponents",
                           "updateDataModel", "deleteSurface"),
    }
    exec(compile("\n\n".join(bodies), TEMPLATE, "exec"), ns)  # noqa: S102
    return ns


def main():
    logger = _Logger()
    ns = load_helpers(logger)
    registry = ns["_session_surface_registry"]
    failures = 0

    def check(name, ok, got):
        nonlocal failures
        failures += 0 if ok else 1
        print("  %-4s %-56s got=%s" % ("ok" if ok else "FAIL", name, got))

    def arm(sid, task):
        # Mirrors _process_request: the guard is armed BEFORE the session (and
        # therefore the registry) is restored, so it holds the dict object.
        ns["_current_surface_guard"].set({
            "registry": ns["_get_surface_registry"](sid), "task": task,
            "suffix": task[:12],
        })

    def emit(kind, sid):
        body = {"surfaceId": sid}
        if kind == "createSurface":
            body["catalogId"] = "c"
        msg = ns["_rescope_reused_surfaces"]({"version": "v0.9", kind: body})
        return msg[kind]["surfaceId"]

    sid = "sess-1"
    print("surface-registry persistence (v11.92)")

    arm(sid, "a" * 12)
    got = emit("createSurface", "analysis-plan")
    check("first render keeps its id", got == "analysis-plan", got)

    arm(sid, "b" * 12)
    got = emit("createSurface", "analysis-plan")
    check("same-process reuse is renamed", got == "analysis-plan-ubbbbbbbbbbbb", got)

    blob = ns["_snapshot_surface_registry"](sid)
    check("snapshot is JSON text, not a Firestore map", isinstance(blob, str),
          type(blob).__name__)
    check("snapshot carries the latest incarnation",
          json.loads(blob).get("analysis-plan", {}).get("current")
          == "analysis-plan-ubbbbbbbbbbbb", blob)

    registry.clear()  # scale-to-zero: the process that held the anchors is gone
    arm(sid, "c" * 12)
    ns["_load_surface_registry"](sid, blob)
    got = emit("createSurface", "analysis-plan")
    check("reuse across a cold start is renamed", got == "analysis-plan-ucccccccccccc", got)
    check("restore is logged",
          any("restored 1 surface id" in line for line in logger.lines),
          [l for l in logger.lines if "restored" in l])
    check("restore mutates the armed dict rather than rebinding it",
          ns["_current_surface_guard"].get()["registry"] is registry[sid], "same object")

    got = emit("deleteSurface", "analysis-plan")
    check("teardown follows the latest incarnation",
          got == "analysis-plan-ucccccccccccc", got)

    # A restored blob is history; whatever this process already rendered is newer.
    registry.clear()
    arm(sid, "d" * 12)
    emit("createSurface", "welcome-card")
    ns["_load_surface_registry"](sid, {"welcome-card": {"current": "welcome-card-uSTALE",
                                                        "owner": "old"}})
    got = registry[sid]["welcome-card"]["current"]
    check("a stale blob never clobbers a live anchor", got == "welcome-card", got)

    registry["big"] = {("k%03d" % i): {"current": "c%d" % i, "owner": "o"}
                       for i in range(120)}
    snap = json.loads(ns["_snapshot_surface_registry"]("big"))
    check("snapshot keeps the newest 50 anchors",
          len(snap) == 50 and "k119" in snap and "k070" in snap and "k069" not in snap,
          len(snap))

    # A surfaceId is model-authored, and Firestore rejects a FIELD name matching
    # __.*__ - as a map that 400 would fail the whole flush, history included.
    registry["odd"] = {"__evil__": {"current": "__evil__-uab", "owner": "t"},
                       "a.b/c": {"current": "a.b/c", "owner": "t"}}
    odd = ns["_snapshot_surface_registry"]("odd")
    check("reserved-looking ids survive as JSON text",
          json.loads(odd).get("__evil__", {}).get("current") == "__evil__-uab", odd[:48])

    ns["_load_surface_registry"]("junk", {"a": None, "b": {"owner": "x"}, "c": "nope"})
    check("malformed stored entries are ignored", not registry.get("junk"),
          registry.get("junk"))
    for bad in (None, "", "not json{", "[]", 7):
        ns["_load_surface_registry"]("junk2", bad)
    check("a missing or corrupt snapshot is survived", "junk2" not in registry, "no-op")
    check("an unseen session snapshots empty",
          ns["_snapshot_surface_registry"]("never-seen") == "{}", "{}")

    if failures:
        print("\n%d case(s) FAILED" % failures)
        return 1
    print("\nAll case(s) passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
