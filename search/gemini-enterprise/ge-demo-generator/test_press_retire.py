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


def load_iframe_healer(logger, fake_tools=None):
    """Exec the A2UI healer out of the template with controllable GCS/tools stubs."""
    src = open(TEMPLATE, encoding="utf-8").read()
    start = src.index("_HEALED_IFRAME_URL_CACHE = {}")
    end = src.index("def _a2ui_iter_msgs(", start)
    ns = {
        "os": os,
        "logger": logger,
        "_a2ui_kind": lambda m: next(
            (k for k in ("createSurface", "updateComponents", "updateDataModel", "deleteSurface")
             if k in m), None),
        "_a2ui_body": lambda m: next(
            (m[k] for k in ("createSurface", "updateComponents", "updateDataModel", "deleteSurface")
             if k in m and isinstance(m[k], dict)), None),
        "_normalize_a2ui_icon_component": lambda c: False,
        "_agent_tools": fake_tools,
    }
    exec(compile(src[start:end], TEMPLATE, "exec"), ns)  # noqa: S102
    return ns


def run_iframe_healer_tests(logger):
    import types

    failures = 0
    print("\niframe-healer (v12.26)")

    sample_html = (
        "<!DOCTYPE html><html><head><style>body{color:red}</style>"
        "<script>alert(1)</script></head><body>"
        "<h2>Regional Performance</h2><div><b>$12.4M</b> Total revenue</div>"
        "</body></html>"
    )

    # 1. Without DASHBOARDS_BUCKET -> falls back to extracted text summary
    os.environ.pop("DASHBOARDS_BUCKET", None)
    ns = load_iframe_healer(logger)
    msgs = [{
        "version": "v0.9",
        "updateComponents": {
            "surfaceId": "dash-1",
            "components": [
                {"id": "root", "component": "MaterialCard", "children": ["frame1"]},
                {"id": "frame1", "component": "IFrameSrcdoc", "height": 260, "htmlContent": sample_html},
            ],
        },
    }]
    healed = ns["_heal_a2ui_message_list"](msgs)
    comp = healed[0]["updateComponents"]["components"][1]
    ok = (
        comp.get("id") == "frame1"
        and comp.get("component") == "MaterialText"
        and comp.get("usageHint") == "body"
        and "Regional Performance" in comp.get("text", "")
        and "$12.4M Total revenue" in comp.get("text", "")
        and "color:red" not in comp.get("text", "")
        and "alert(1)" not in comp.get("text", "")
        and "htmlContent" not in comp
        and "height" not in comp
    )
    failures += 0 if ok else 1
    print("  %-4s %-52s got=%r" % ("ok" if ok else "FAIL", "IFrameSrcdoc without bucket extracts clean text", comp))

    # 2. With DASHBOARDS_BUCKET and stubbed GCS + _generate_v4_signed_url
    uploaded = []

    class _FakeBlob:
        def __init__(self, name):
            self.name = name

        def upload_from_string(self, data, content_type=None):
            uploaded.append((self.name, data, content_type))

    class _FakeBucket:
        def blob(self, name):
            return _FakeBlob(name)

    class _FakeClient:
        def bucket(self, name):
            return _FakeBucket()

    fake_storage = types.ModuleType("google.cloud.storage")
    fake_storage.Client = _FakeClient
    fake_cloud = types.ModuleType("google.cloud")
    fake_cloud.storage = fake_storage
    fake_google = types.ModuleType("google")
    fake_google.cloud = fake_cloud
    saved_mods = {k: sys.modules.get(k) for k in ("google", "google.cloud", "google.cloud.storage")}
    sys.modules["google"] = fake_google
    sys.modules["google.cloud"] = fake_cloud
    sys.modules["google.cloud.storage"] = fake_storage

    fake_tools = types.SimpleNamespace(
        _generate_v4_signed_url=lambda b, o, ct: f"https://storage.googleapis.com/{b}/{o}?sig=v4"
    )
    try:
        os.environ["DASHBOARDS_BUCKET"] = "test-dash-bucket"
        ns = load_iframe_healer(logger, fake_tools=fake_tools)
        msgs2 = [{
            "version": "v0.9",
            "updateComponents": {
                "surfaceId": "dash-2",
                "components": [
                    {"id": "frame2", "component": "IFrameSrcdoc", "height": 300, "htmlContent": sample_html},
                ],
            },
        }]
        ns["_heal_a2ui_message_list"](msgs2)
        comp2 = msgs2[0]["updateComponents"]["components"][0]
        ok2 = (
            comp2.get("id") == "frame2"
            and comp2.get("component") == "MaterialText"
            and "[Open Interactive Dashboard](https://storage.googleapis.com/test-dash-bucket/dashboards/dash_" in comp2.get("text", "")
            and "Regional Performance" in comp2.get("text", "")
            and len(uploaded) == 1
        )
        failures += 0 if ok2 else 1
        print("  %-4s %-52s uploads=%d" % ("ok" if ok2 else "FAIL", "IFrameSrcdoc with bucket uploads & signs V4 URL", len(uploaded)))

        # 3. Cache hit on identical HTML in same bucket avoids duplicate upload
        msgs3 = [{
            "version": "v0.9",
            "updateComponents": {
                "surfaceId": "dash-3",
                "components": [
                    {"id": "frame3", "component": "IFrameSrcdoc", "htmlContent": sample_html},
                ],
            },
        }]
        ns["_heal_a2ui_message_list"](msgs3)
        ok3 = len(uploaded) == 1 and "[Open Interactive Dashboard](" in msgs3[0]["updateComponents"]["components"][0].get("text", "")
        failures += 0 if ok3 else 1
        print("  %-4s %-52s uploads=%d" % ("ok" if ok3 else "FAIL", "IFrameSrcdoc cache hit skips duplicate GCS upload", len(uploaded)))

        # 4. Upload exception falls back to text summary cleanly
        fake_tools_err = types.SimpleNamespace(
            _generate_v4_signed_url=lambda b, o, ct: (_ for _ in ()).throw(RuntimeError("IAM signBlob denied"))
        )
        ns_err = load_iframe_healer(logger, fake_tools=fake_tools_err)
        msgs4 = [{
            "version": "v0.9",
            "updateComponents": {
                "surfaceId": "dash-4",
                "components": [
                    {"id": "frame4", "component": "IFrameSrcdoc", "htmlContent": sample_html},
                ],
            },
        }]
        ns_err["_heal_a2ui_message_list"](msgs4)
        comp4 = msgs4[0]["updateComponents"]["components"][0]
        ok4 = (
            comp4.get("component") == "MaterialText"
            and "Regional Performance" in comp4.get("text", "")
            and "Open Interactive Dashboard" not in comp4.get("text", "")
        )
        failures += 0 if ok4 else 1
        print("  %-4s %-52s got=%r" % ("ok" if ok4 else "FAIL", "IFrameSrcdoc sign failure falls back to summary", comp4.get("text")))
    finally:
        os.environ.pop("DASHBOARDS_BUCKET", None)
        for k, v in saved_mods.items():
            if v is not None:
                sys.modules[k] = v
            else:
                sys.modules.pop(k, None)

    # 5. Empty IFrameSrcdoc and IFrameUrl edge cases
    msgs5 = [{
        "version": "v0.9",
        "updateComponents": {
            "surfaceId": "dash-5",
            "components": [
                {"id": "emptyFrame", "component": "IFrameSrcdoc", "htmlContent": ""},
                {"id": "urlFrame", "component": "IFrameUrl", "url": "https://example.com/report"},
                {"id": "emptyUrlFrame", "component": "IFrameUrl", "url": ""},
            ],
        },
    }]
    ns["_heal_a2ui_message_list"](msgs5)
    c_empty, c_url, c_empty_url = msgs5[0]["updateComponents"]["components"]
    ok5 = (
        c_empty.get("component") == "MaterialText" and bool(c_empty.get("text"))
        and c_url.get("component") == "MaterialText"
        and c_url.get("text") == "📊 [Open Interactive View](https://example.com/report)"
        and c_empty_url.get("component") == "MaterialText" and bool(c_empty_url.get("text"))
    )
    failures += 0 if ok5 else 1
    print("  %-4s %-52s url=%r" % ("ok" if ok5 else "FAIL", "empty IFrameSrcdoc and IFrameUrl edge cases", c_url.get("text")))

    return failures


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

    failures += run_iframe_healer_tests(logger)

    if failures:
        print("\n%d case(s) FAILED" % failures)
        return 1
    print("\nAll %d case(s) passed." % (len(CASES) + 1 + 5))
    return 0


if __name__ == "__main__":
    sys.exit(main())
