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

"""Evaluation of the system: routing, scene reliability, pixels versus code, markup and latency.

Run from the project folder:  python eval/run_eval.py --out eval/results
"""

import argparse
import asyncio
import base64
import html
import json
import os
import re
import statistics
import sys
import threading
import time
from collections import Counter, defaultdict
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

import websockets  # noqa: E402
from google.genai import types  # noqa: E402

import server  # noqa: E402
from voxplore import (  # noqa: E402
    SetupMessage,
    app_name,
    genmedia,
    get_agent_setup_config,
    root_agent,
)
from voxplore.tools import (  # noqa: E402
    SessionState,
    annotate_current_view,
    current_session,
)

STAGES = ["routing", "scenes", "compare", "markup", "video"]
MEDIUM = {
    "generate_image": "image",
    "generate_video": "video",
    "generate_interactive_scene": "scene",
    "generate_illustrated_scene": "illustrated",
    "annotate_current_view": "annotate",
    "edit_image": "edit",
    "edit_video": "edit",
    "edit_interactive_scene": "edit",
}


def load_requests(path: Path, limit: int) -> list:
    items = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not limit:
        return items
    # the same number from each category, so a short run still covers every medium
    kept, seen = [], Counter()
    for item in items:
        if seen[item["category"]] < limit:
            seen[item["category"]] += 1
            kept.append(item)
    return kept


async def stream_frame(ws, frame: bytes):
    """Sends the frame once per second, like the app does with the camera."""
    video = {"mimeType": "image/jpeg", "data": base64.b64encode(frame).decode("ascii")}
    try:
        while True:
            await ws.send(json.dumps({"realtimeInput": {"video": video}}))
            await asyncio.sleep(1)
    except Exception:
        pass


async def route(request: str, frame: bytes = None, timeout: float = 40.0) -> dict:
    """Sends one request to the live model with the app's own setup and reports which tool it calls."""
    setup = SetupMessage.model_validate(get_agent_setup_config(root_agent))
    url = server.get_vertex_url()
    headers = server.get_vertex_headers()
    ssl_context = server.get_ssl_context() if url.startswith("wss://") else None
    result = {"tools": [], "spoken": "", "seconds_to_tool": None}
    spoken = []
    streams = []

    async def converse(ws):
        asked_at = None
        async for raw in ws:
            text = raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else raw
            try:
                message = json.loads(text)
            except ValueError:
                continue
            if message.get("error"):
                result["error"] = json.dumps(message["error"])
                return
            if "setupComplete" in message:
                if frame:
                    streams.append(asyncio.create_task(stream_frame(ws, frame)))
                    await asyncio.sleep(3)
                await ws.send(json.dumps({"realtimeInput": {"text": request}}))
                asked_at = time.monotonic()
                continue
            tool_call = message.get("toolCall")
            if tool_call:
                result["tools"] = [
                    {"name": call.get("name"), "args": call.get("args") or {}}
                    for call in tool_call.get("functionCalls", [])
                ]
                result["seconds_to_tool"] = (
                    round(time.monotonic() - asked_at, 2) if asked_at else None
                )
                return
            content = message.get("serverContent") or {}
            transcript = (content.get("outputTranscription") or {}).get("text")
            if transcript:
                spoken.append(transcript)
            if content.get("turnComplete"):
                return

    try:
        async with websockets.connect(
            url, additional_headers=headers or None, ssl=ssl_context, max_size=None
        ) as ws:
            await ws.send(setup.model_dump_json(by_alias=True, exclude_none=True))
            try:
                await asyncio.wait_for(converse(ws), timeout)
            finally:
                for stream in streams:
                    stream.cancel()
    except asyncio.TimeoutError:
        result["error"] = "timeout"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    result["spoken"] = " ".join(spoken).strip()
    return result


def chosen_medium(routed: dict) -> str:
    if routed.get("error"):
        return "error"
    if not routed["tools"]:
        return "none"
    return MEDIUM.get(routed["tools"][0]["name"], "other")


HOST_PAGE = """<!DOCTYPE html><html><body style="margin:0;background:#000"><script>
window.__events = [];
window.addEventListener('message', (e) => { if (e.data && e.data.scene === true) window.__events.push(e.data); });
window.__load = (html) => {
  const old = document.querySelector('iframe');
  if (old) old.remove();
  window.__events = [];
  const frame = document.createElement('iframe');
  frame.setAttribute('sandbox', 'allow-scripts');
  frame.style.cssText = 'border:0;width:100vw;height:100vh;display:block';
  frame.srcdoc = html;
  document.body.appendChild(frame);
};
</script></body></html>"""


class FrontendHandler(SimpleHTTPRequestHandler):
    """Serves frontend/ like server.py does, so scenes import three.js from /vendor the same way."""

    def do_GET(self):
        if self.path == "/__host":
            body = HOST_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, *args):
        pass


CHECK_TIMEOUT_SECONDS = 25


class SceneBrowser:
    """Loads a scene in headless Chrome, in the same sandboxed iframe as the app."""

    def __init__(self, settle_seconds: float):
        self.settle_seconds = settle_seconds

    async def __aenter__(self):
        from playwright.async_api import async_playwright

        self.httpd = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(FrontendHandler, directory=str(ROOT / "frontend"))
        )
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.playwright = await async_playwright().start()
        await self.launch()
        return self

    async def launch(self):
        options = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--enable-unsafe-swiftshader",
                "--use-gl=angle",
                "--use-angle=swiftshader",
            ],
        }
        if os.environ.get("CHROME_PATH"):
            options["executable_path"] = os.environ["CHROME_PATH"]
        self.browser = await self.playwright.chromium.launch(**options)
        self.page = await self.browser.new_page(viewport={"width": 1024, "height": 640})
        await self.page.goto(f"http://127.0.0.1:{self.httpd.server_address[1]}/__host")

    async def __aexit__(self, *exc):
        try:
            await asyncio.wait_for(self.browser.close(), 5)
        except Exception:
            pass
        await self.playwright.stop()
        self.httpd.shutdown()

    async def check(self, html: str, screenshot: Path) -> dict:
        limit = self.settle_seconds + CHECK_TIMEOUT_SECONDS
        try:
            return await asyncio.wait_for(self.inspect(html, screenshot), limit)
        except Exception as e:
            # a scene that keeps the page busy, or renders too slowly without a graphics card, must not stop
            # the run: the browser is replaced and the scene is recorded as timed out
            reason = (
                str(e).splitlines()
                or [f"no answer from the page within {limit:.0f} seconds"]
            )[0]
            try:
                await asyncio.wait_for(self.browser.close(), 5)
            except Exception:
                pass
            await self.launch()
            return {
                "errors": [],
                "has_canvas": False,
                "counts": None,
                "events": [],
                "timed_out": reason,
            }

    async def inspect(self, html: str, screenshot: Path) -> dict:
        await self.page.evaluate("html => window.__load(html)", html)
        await self.page.wait_for_timeout(int(self.settle_seconds * 1000))
        events = await self.page.evaluate("window.__events")
        errors = [str(e.get("message")) for e in events if e.get("type") == "error"]
        canvases = await self.page.frame_locator("iframe").locator("canvas").count()
        counts = None
        if len(self.page.frames) > 1:
            counts = await self.page.frames[-1].evaluate(
                "window.__stage ? window.__stage.counts() : null"
            )
        await self.page.screenshot(path=str(screenshot))
        return {
            "errors": errors,
            "has_canvas": canvases > 0,
            "counts": counts,
            "events": [e.get("name") for e in events if e.get("type") == "event"],
        }


def saved_scene(item: dict, out: Path) -> Path | None:
    for extension in ("js", "html"):
        if (out / f"{item['id']}.{extension}").exists():
            return out / f"{item['id']}.{extension}"
    return None


async def run_scene(
    item: dict, browser: SceneBrowser, out: Path, previous: dict | None = None
) -> dict:
    """Generates one scene, runs it, and applies the app's single repair if it fails. With previous, the scene
    that an earlier run generated and could not check in time is checked again, without generating it anew.
    """
    record = {"id": item["id"], "request": item["request"]}
    description = item.get("description") or item["request"]
    saved = saved_scene(item, out) if previous else None
    if saved:
        source = saved.read_text(encoding="utf-8")
        record["generate_seconds"] = previous.get("generate_seconds")
        record["rechecked"] = True
    else:
        started = time.monotonic()
        try:
            source = await genmedia.generate_scene(description)
        except Exception as e:
            return {**record, "outcome": "generation_error", "error": str(e)}
        record["generate_seconds"] = round(time.monotonic() - started, 2)
        saved = out / f"{item['id']}.{'html' if genmedia.is_page(source) else 'js'}"
        saved.write_text(source, encoding="utf-8")
    record["lines"] = source.count("\n") + 1
    if browser is None:
        return {**record, "outcome": "not_run"}

    screenshot = out / f"{item['id']}_scene.png"
    check = await browser.check(
        genmedia.scene_media(source).data.decode("utf-8"), screenshot
    )
    if check.get("timed_out"):
        return {**record, "outcome": "timed_out", "error": check["timed_out"]}
    record["first_errors"] = check["errors"]
    if check["errors"]:
        started = time.monotonic()
        try:
            source = await genmedia.fix_scene(source, check["errors"][0])
        except Exception as e:
            return {**record, "outcome": "failed", "error": str(e)}
        record["repair_seconds"] = round(time.monotonic() - started, 2)
        saved.write_text(source, encoding="utf-8")
        check = await browser.check(
            genmedia.scene_media(source).data.decode("utf-8"), screenshot
        )
        if check.get("timed_out"):
            return {**record, "outcome": "timed_out", "error": check["timed_out"]}
        record["repair_errors"] = check["errors"]
        outcome = "failed" if check["errors"] else "ok_after_repair"
    else:
        outcome = "ok_first"
    if outcome != "failed" and not check["has_canvas"]:
        outcome = "no_canvas"
    if check.get("counts"):
        record["parts"] = check["counts"]["parts"]
        record["controls"] = check["counts"]["sliders"] + check["counts"]["buttons"]
    return {**record, "outcome": outcome, "screenshot": screenshot.name}


def judge_model() -> str:
    return os.environ.get("JUDGE_MODEL", "gemini-4-argon")


JUDGE_PROMPT = """You are checking an educational visual against a list of facts.
For each fact, look only at what the picture shows and answer with one of:
- "correct": the picture shows this and it is right
- "incorrect": the picture contradicts this
- "not_shown": the picture does not show enough to tell
Be strict about counts, order, spelling and formulas.
Return JSON: {"verdicts": [...]} with exactly one verdict per fact, in order.

Facts:
"""


def _judge_sync(image: bytes, mime_type: str, facts: list) -> list:
    client = genmedia.get_client(os.environ.get("JUDGE_MODEL_LOCATION", "global"))
    prompt = JUDGE_PROMPT + "\n".join(
        f"{i + 1}. {fact}" for i, fact in enumerate(facts)
    )
    response = client.models.generate_content(
        model=judge_model(),
        contents=[types.Part.from_bytes(data=image, mime_type=mime_type), prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json", temperature=0
        ),
    )
    verdicts = json.loads(response.text)["verdicts"]
    if len(verdicts) != len(facts):
        raise ValueError(
            f"judge returned {len(verdicts)} verdicts for {len(facts)} facts"
        )
    return verdicts


async def judge(image: bytes, mime_type: str, facts: list) -> list:
    return await asyncio.to_thread(_judge_sync, image, mime_type, facts)


async def run_compare(
    item: dict, scene: dict, out: Path, previous: dict | None = None
) -> dict:
    """Same request as pixels (Nano Banana) and as code (the scene's screenshot), judged on the same facts.
    With previous, the image verdict of an earlier run is kept and only the scene is judged.
    """
    record = {"id": item["id"], "facts": item["facts"]}
    started = time.monotonic()
    if previous and "pixels" in previous:
        record.update(
            {
                key: previous[key]
                for key in ("pixels", "image_seconds")
                if key in previous
            }
        )
    else:
        try:
            prompt = f"An accurate, clearly labeled educational diagram. {item.get('description') or item['request']}"
            image = await genmedia.generate_image(prompt, "16:9")
            record["image_seconds"] = round(time.monotonic() - started, 2)
            extension = image.mime_type.split("/")[-1]
            (out / f"{item['id']}_pixels.{extension}").write_bytes(image.data)
            record["pixels"] = await judge(image.data, image.mime_type, item["facts"])
        except Exception as e:
            record["pixels_error"] = str(e)
    screenshot = (
        out / scene["screenshot"] if scene and scene.get("screenshot") else None
    )
    if screenshot and scene["outcome"] in ("ok_first", "ok_after_repair"):
        try:
            record["code"] = await judge(
                screenshot.read_bytes(), "image/png", item["facts"]
            )
        except Exception as e:
            record["code_error"] = str(e)
    else:
        record["code_error"] = "no working scene to judge"
    return record


async def run_markup(item: dict, out: Path) -> dict:
    """Runs the annotate tool on a frame and saves the result; the marking itself is reviewed by a person."""
    frame = (EVAL_DIR / item["frame"]).read_bytes()
    token = current_session.set(SessionState(last_frame=("image/jpeg", frame)))
    started = time.monotonic()
    try:
        media = await annotate_current_view(item["request"])
    except Exception as e:
        return {"id": item["id"], "error": str(e)}
    finally:
        current_session.reset(token)
    name = f"{item['id']}_markup.{media.mime_type.split('/')[-1]}"
    (out / name).write_bytes(media.data)
    return {
        "id": item["id"],
        "expected": item["markup"],
        "finding": media.note,
        "seconds": round(time.monotonic() - started, 2),
        "file": name,
    }


async def run_video(item: dict) -> dict:
    started = time.monotonic()
    try:
        await genmedia.generate_video(item["request"], "16:9")
    except Exception as e:
        return {"id": item["id"], "error": str(e)}
    return {"id": item["id"], "seconds": round(time.monotonic() - started, 2)}


def percentile(values: list, fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))]


def timing_row(label: str, values: list) -> str:
    values = [v for v in values if v is not None]
    if not values:
        return f"| {label} | 0 | | |"
    return f"| {label} | {len(values)} | {statistics.median(values):.1f} | {percentile(values, 0.9):.1f} |"


def share(part: int, whole: int) -> str:
    return f"{part}/{whole} ({100 * part / whole:.0f}%)" if whole else "0/0"


def write_report(results: dict, out: Path):
    lines = [
        f"# {app_name()} evaluation",
        "",
        f"Live model: `{root_agent.model}`. Image: `{genmedia.image_model()}`. Video: `{genmedia.video_model()}`. "
        f"Scene: `{genmedia.scene_model()}`. Judge: `{judge_model()}`.",
        "",
    ]

    routing = results.get("routing")
    if routing:
        by_category = defaultdict(list)
        for record in routing:
            by_category[record["category"]].append(record)
        media = [
            "none",
            "image",
            "video",
            "scene",
            "illustrated",
            "annotate",
            "edit",
            "other",
            "error",
        ]
        lines += [
            "## Routing",
            "",
            "A request counts as correct when the first tool the live model calls is one of the expected media "
            "(or no tool when none is expected).",
            "",
            f"Overall: {share(sum(r['correct'] for r in routing), len(routing))}",
            "",
            "| Expected | Correct | " + " | ".join(media) + " |",
            "|---|---|" + "---|" * len(media),
        ]
        for category, records in by_category.items():
            chosen = Counter(r["chosen"] for r in records)
            lines.append(
                f"| {category} | {share(sum(r['correct'] for r in records), len(records))} | "
                + " | ".join(str(chosen.get(m, 0)) for m in media)
                + " |"
            )
        wrong = [r for r in routing if not r["correct"]]
        if wrong:
            lines += ["", "Misrouted requests:", ""]
            lines += [
                f'- {r["id"]}: "{r["request"]}" expected {"/".join(r["expected"])}, got {r["chosen"]}'
                for r in wrong
            ]
        lines.append("")

    scenes = results.get("scenes")
    if scenes:
        outcomes = Counter(s["outcome"] for s in scenes)
        total = len(scenes)
        lines += [
            "## Scene reliability",
            "",
            "Each scene is generated once, loaded in headless Chrome in the app's sandboxed iframe, and given "
            "the app's single automatic repair if it raises a script error.",
            "",
            "| Outcome | Scenes |",
            "|---|---|",
        ]
        for outcome in [
            "ok_first",
            "ok_after_repair",
            "failed",
            "no_canvas",
            "timed_out",
            "generation_error",
            "not_run",
        ]:
            if outcomes.get(outcome):
                lines.append(f"| {outcome} | {share(outcomes[outcome], total)} |")
        counted = [s for s in scenes if "parts" in s]
        if counted:
            lines += [
                "",
                f"Scenes with clickable parts: {share(sum(1 for s in counted if s['parts']), len(counted))}. "
                f"With sliders or buttons: {share(sum(1 for s in counted if s['controls']), len(counted))}.",
            ]
        rechecked = [s["id"] for s in scenes if s.get("rechecked")]
        if rechecked:
            lines += [
                "",
                f"Checked a second time, from the code saved by the first run, after the headless browser "
                f"gave no answer: {', '.join(rechecked)}.",
            ]
        failed = [
            s
            for s in scenes
            if s["outcome"] in ("failed", "no_canvas", "timed_out", "generation_error")
        ]
        if failed:
            lines += ["", "Failures:", ""]
            for s in failed:
                reason = (
                    s.get("repair_errors")
                    or s.get("first_errors")
                    or [s.get("error", "")]
                )[0]
                lines.append(f'- {s["id"]}: "{s["request"]}" ({s["outcome"]}) {reason}')
        lines.append("")

    compare = results.get("compare")
    if compare:
        lines += [
            "## Pixels versus code",
            "",
            "The same request rendered by the image model and by a generated scene, each checked by the judge "
            "model against the same facts. Judged by a model, so spot-check the saved files.",
            "",
            "| Medium | Requests judged | Correct | Incorrect | Not shown |",
            "|---|---|---|---|---|",
        ]
        for key, label in [
            ("pixels", "Pixels (image model)"),
            ("code", "Code (scene)"),
        ]:
            verdicts = [v for record in compare for v in record.get(key, [])]
            counts = Counter(verdicts)
            judged = sum(1 for record in compare if key in record)
            lines.append(
                f"| {label} | {judged} | {share(counts.get('correct', 0), len(verdicts))} | "
                f"{share(counts.get('incorrect', 0), len(verdicts))} | {share(counts.get('not_shown', 0), len(verdicts))} |"
            )
        both = [r for r in compare if "pixels" in r and "code" in r]
        if both:
            lines += [
                "",
                f"On the {len(both)} requests where both were judged:",
                "",
                "| Request | Pixels correct | Code correct |",
                "|---|---|---|",
            ]
            for r in both:
                lines.append(
                    f"| {r['id']} | {r['pixels'].count('correct')}/{len(r['facts'])} | "
                    f"{r['code'].count('correct')}/{len(r['facts'])} |"
                )
        lines.append("")

    markup = results.get("markup")
    if markup:
        lines += [
            "## Markup on a camera frame",
            "",
            "The tool reads the frame, then draws on it. Check by eye: does the finding match the expected "
            "mistake, is the right thing marked, and is the frame otherwise unchanged?",
            "",
        ]
        for m in markup:
            if m.get("error"):
                lines.append(f"- {m['id']}: error: {m['error']}")
            else:
                lines.append(
                    f"- {m['id']}: {m['file']}. Found: {m.get('finding')} Expected: {m.get('expected')}"
                )
        lines.append("")

    lines += [
        "## Latency (seconds)",
        "",
        "| Step | Runs | Median | p90 |",
        "|---|---|---|---|",
    ]
    if routing:
        lines.append(
            timing_row(
                "Live model, request to tool call",
                [r.get("seconds_to_tool") for r in routing],
            )
        )
    if compare:
        lines.append(
            timing_row("Image generation", [r.get("image_seconds") for r in compare])
        )
    if scenes:
        lines.append(
            timing_row("Scene generation", [s.get("generate_seconds") for s in scenes])
        )
        lines.append(
            timing_row("Scene repair", [s.get("repair_seconds") for s in scenes])
        )
    if markup:
        lines.append(timing_row("Markup", [m.get("seconds") for m in markup]))
    if results.get("video"):
        lines.append(
            timing_row("Video generation", [v.get("seconds") for v in results["video"]])
        )
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # the app shows a Results link in its header when this page exists
    (ROOT / "frontend" / "results.html").write_text(
        report_page(lines), encoding="utf-8"
    )


PAGE_STYLE = """
body { margin: 0; padding: 40px 24px; background: #1c2530; color: #e9eef3; font-family: 'Google Sans Flex', 'Google Sans', 'Roboto', system-ui, sans-serif; line-height: 1.5; }
main { max-width: 980px; margin: 0 auto; }
h1 { font-size: 1.8rem; margin: 0 0 12px; }
h2 { font-size: 1.25rem; margin: 36px 0 10px; color: #cfe4ff; }
p, li { color: #c3ced9; }
code { background: rgba(255, 255, 255, 0.08); padding: 1px 6px; border-radius: 4px; font-size: 0.9em; }
table { border-collapse: collapse; margin: 12px 0; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 7px 14px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
th { color: #9aa8b8; font-weight: 500; font-size: 0.85rem; }
"""


def report_page(lines: list) -> str:
    """The report as a standalone page, from the same lines as report.md."""

    def inline(text):
        return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text))

    body, table, items = [], [], []

    def flush():
        if table:
            head, rows = table[0], table[2:]
            body.append(
                "<table><tr>"
                + "".join(f"<th>{inline(c)}</th>" for c in head)
                + "</tr>"
                + "".join(
                    "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>"
                    for row in rows
                )
                + "</table>"
            )
            table.clear()
        if items:
            body.append(
                "<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>"
            )
            items.clear()

    for line in lines:
        if line.startswith("|"):
            table.append([cell.strip() for cell in line.strip().strip("|").split("|")])
            continue
        if line.startswith("- "):
            items.append(line[2:])
            continue
        flush()
        if line.startswith("## "):
            body.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("# "):
            body.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.strip():
            body.append(f"<p>{inline(line)}</p>")
    flush()
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>'
        + app_name()
        + " evaluation</title>"
        '<link href="https://fonts.googleapis.com/css2?family=Google+Sans+Flex:wght@400;500;600;700&display=swap" rel="stylesheet">'
        f"<style>{PAGE_STYLE}</style></head><body><main>{''.join(body)}</main></body></html>\n"
    )


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=Path, default=EVAL_DIR / "requests.jsonl")
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results")
    parser.add_argument(
        "--stages",
        default="routing,scenes,compare,markup",
        help=f"comma-separated, from: {', '.join(STAGES)}. video is off by default (slow and costly)",
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="requests per category, for a quick run"
    )
    parser.add_argument(
        "--videos",
        type=int,
        default=3,
        help="how many videos the video stage generates",
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="generate scenes without running them"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="continue a run that stopped: keep what results.json in --out already holds",
    )
    parser.add_argument(
        "--settle-seconds",
        type=float,
        default=4.0,
        help="how long a scene runs before it is checked",
    )
    args = parser.parse_args()

    stages = [s.strip() for s in args.stages.split(",") if s.strip()]
    if (
        "scenes" in stages
        and not (ROOT / "frontend" / "vendor" / "three.module.js").is_file()
    ):
        sys.exit(
            "three.js is missing, so scenes cannot run. Run: python fetch_three.py"
        )
    unknown = [s for s in stages if s not in STAGES]
    if unknown:
        parser.error(f"unknown stages: {', '.join(unknown)}")
    args.out.mkdir(parents=True, exist_ok=True)
    items = load_requests(args.requests, args.limit)
    results = {}
    if args.resume and (args.out / "results.json").exists():
        results = json.loads((args.out / "results.json").read_text(encoding="utf-8"))

    def done(stage: str) -> set:
        return {record["id"] for record in results.get(stage, [])}

    def save():
        (args.out / "results.json").write_text(
            json.dumps(results, indent=2), encoding="utf-8"
        )
        write_report(results, args.out)

    if "routing" in stages:
        results.setdefault("routing", [])
        for item in items:
            if item["id"] in done("routing"):
                continue
            frame = (
                (EVAL_DIR / item["frame"]).read_bytes() if item.get("frame") else None
            )
            routed = await route(item["request"], frame)
            chosen = chosen_medium(routed)
            results["routing"].append(
                {
                    "id": item["id"],
                    "category": item["category"],
                    "request": item["request"],
                    "expected": item["expected"],
                    "chosen": chosen,
                    "correct": chosen in item["expected"],
                    **routed,
                }
            )
            print(
                f"routing {item['id']}: {chosen} ({'ok' if chosen in item['expected'] else 'expected ' + '/'.join(item['expected'])})",
                flush=True,
            )
            save()

    scene_items = [item for item in items if item["category"] in ("scene", "hard")]
    if "scenes" in stages or "compare" in stages:
        results.setdefault("scenes", [])
        browser = None if args.no_browser else SceneBrowser(args.settle_seconds)
        if browser:
            await browser.__aenter__()
        try:
            for item in scene_items:
                earlier = next(
                    (s for s in results["scenes"] if s["id"] == item["id"]), None
                )
                if earlier and not (earlier["outcome"] == "timed_out" and browser):
                    continue
                record = await run_scene(item, browser, args.out, earlier)
                if earlier:
                    results["scenes"].remove(earlier)
                results["scenes"].append(record)
                print(f"scene {item['id']}: {record['outcome']}", flush=True)
                save()
        finally:
            if browser:
                await browser.__aexit__(None, None, None)

    if "compare" in stages:
        results.setdefault("compare", [])
        scenes_by_id = {s["id"]: s for s in results["scenes"]}
        for item in scene_items:
            if not item.get("facts"):
                continue
            scene = scenes_by_id.get(item["id"])
            earlier = next(
                (c for c in results["compare"] if c["id"] == item["id"]), None
            )
            if earlier and (
                "code" in earlier
                or not scene
                or scene["outcome"] not in ("ok_first", "ok_after_repair")
            ):
                continue
            record = await run_compare(item, scene, args.out, earlier)
            if earlier:
                results["compare"].remove(earlier)
            results["compare"].append(record)
            print(
                f"compare {item['id']}: pixels {record.get('pixels', record.get('pixels_error'))}, "
                f"code {record.get('code', record.get('code_error'))}",
                flush=True,
            )
            save()

    if "markup" in stages:
        results.setdefault("markup", [])
        for item in items:
            if item.get("markup") and item["id"] not in done("markup"):
                results["markup"].append(await run_markup(item, args.out))
                save()

    if "video" in stages:
        results["video"] = []
        for item in [i for i in items if i["category"] == "video"][: args.videos]:
            results["video"].append(await run_video(item))
            save()

    save()
    print(f"Report: {args.out / 'report.md'}")


if __name__ == "__main__":
    asyncio.run(main())
