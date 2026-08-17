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
"""Run every repo offered in the cockpit UI through the full pipeline, one at a
time, and print a comparable metrics table.

SEQUENTIAL on purpose: running ports concurrently makes `install` and `verify`
fight over CPU and the uv cache, which inflates those numbers by ~40s and makes
the timings useless as a "how fast is the port" measurement.

Usage:
    .venv/bin/python scripts/validate_examples.py [slug ...]

Requires a cockpit already serving on --port (default 7001).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request

# The exact repos the cockpit's "TRY" chips point at (frontend/index.html).
EXAMPLES = {
    "react": "https://github.com/langchain-ai/react-agent.git",
    "odr": "https://github.com/langchain-ai/open_deep_research",
    "crew": "https://github.com/crewAIInc/crewAI-examples/tree/main/crews/marketing_strategy",
    "autogen": "https://github.com/microsoft/autogen/tree/main/python/samples/agentchat_chess_game",
}


def run_port(base: str, repo: str, out_path: str, timeout: int = 2400) -> str:
    req = urllib.request.Request(
        f"{base}/api/port",
        data=json.dumps({"repo": repo}).encode(),
        headers={"Content-Type": "application/json"},
    )
    chunks: list[str] = []
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            chunks.append(raw.decode("utf-8", "replace"))
    text = "".join(chunks)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


def event(text: str, name: str):
    # SSE frames are CRLF-terminated (sse-starlette). The \r has to be tolerated
    # here or every lookup silently returns None and the table prints all-None.
    m = re.search(rf"^event: {name}\r?\ndata: (.*?)\r?$", text, re.M)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*", default=list(EXAMPLES))
    ap.add_argument("--port", type=int, default=7001)
    args = ap.parse_args()
    base = f"http://127.0.0.1:{args.port}"

    rows = []
    for slug in args.slugs or list(EXAMPLES):
        repo = EXAMPLES[slug]
        print(f"\n=== {slug}: {repo}", flush=True)
        t0 = time.time()
        try:
            text = run_port(base, repo, f"/tmp/seq_{slug}.txt")
        except Exception as e:
            print(f"    TRANSPORT FAILURE: {type(e).__name__}: {e}", flush=True)
            rows.append({"slug": slug, "fatal": f"{type(e).__name__}: {e}"})
            continue

        done = event(text, "done") or {}
        met = event(text, "metrics") or {}
        fid = event(text, "fidelity") or {}
        deps = event(text, "deps")
        cases = fid.get("cases") or []
        row = {
            "slug": slug,
            "framework": (event(text, "framework") or {}).get("framework"),
            "target": done.get("target_name"),
            "green": done.get("build_green"),
            "repairs": done.get("repairs"),
            "files": met.get("files"),
            "risks": met.get("risks"),
            "t": met.get("timings_s") or {},
            "fidelity": fid.get("score"),
            "pass_n": sum(1 for c in cases if c.get("verdict") == "pass"),
            "cases_n": len(cases),
            "chat_ready": "event: chat_ready" in text,
            "errors": text.count("event: error"),
            "deps": deps,
            "wall": round(time.time() - t0, 1),
        }
        rows.append(row)
        print(
            f"    green={row['green']} repairs={row['repairs']} "
            f"fidelity={row['fidelity']} ({row['pass_n']}/{row['cases_n']}) "
            f"chat={row['chat_ready']} total={row['t'].get('total')}s",
            flush=True,
        )
        if deps:
            print(f"    deps: {deps}", flush=True)

    print("\n\n================ SUMMARY ================")
    hdr = (
        f"{'example':9} {'framework':10} {'green':6} {'rep':4} {'files':6} "
        f"{'fid':6} {'chat':5} {'intake':7} {'swarm':7} {'plan':6} "
        f"{'codegen':8} {'install':8} {'verify':7} {'TOTAL':7}"
    )
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        if r.get("fatal"):
            print(f"{r['slug']:9} FATAL: {r['fatal']}")
            continue
        t = r["t"]
        print(
            f"{r['slug']:9} {r['framework']!s:10} {r['green']!s:6} "
            f"{r['repairs']!s:4} {r['files']!s:6} "
            f"{r['fidelity']!s:6} {str(r['chat_ready'])[:5]:5} "
            f"{t.get('intake')!s:7} {t.get('analysis')!s:7} "
            f"{t.get('planning')!s:6} {t.get('codegen')!s:8} "
            f"{t.get('install')!s:8} {t.get('verify')!s:7} "
            f"{t.get('total')!s:7}"
        )

    ok = all(
        (not r.get("fatal"))
        and r.get("green")
        and r.get("chat_ready")
        and (r.get("fidelity") or 0) >= 0.5
        for r in rows
    )
    print("\nGATE:", "ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
