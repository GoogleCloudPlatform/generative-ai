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

# ruff: noqa: INP001

"""End-to-end concurrency and P95 latency tester for an ADK agent on Cloud Run.

Drives the full `adk api_server` request lifecycle over HTTPS:
1. `GET /list-apps` to discover the deployed application name (`app`).
2. `POST /apps/{app_name}/users/{user_id}/sessions` per simulated user.
3. `POST /run` forwarding any `--session-affinity` cookie returned by session
   creation so multi-turn state routes back to the same Cloud Run container.
"""

import argparse
import asyncio
import os
import statistics
import sys
import time
import uuid
from collections import Counter
from dataclasses import dataclass

import httpx

_HTTP_OK = 200


@dataclass(frozen=True)
class CloudRunTarget:
    """Connection parameters shared by simulated concurrent Cloud Run users."""

    base_url: str
    app_name: str
    bearer_token: str
    prompt: str


@dataclass
class CloudRunMetric:
    """Latency, HTTP status, and response preview for a single user request."""

    user_id: int
    status_code: int
    latency_s: float
    ok: bool
    preview: str = ""
    error: str = ""


def extract_adk_event_text(events: list | dict) -> str:
    """Concatenates all text parts emitted by ADK's `/run` JSON event list."""
    event_list = events if isinstance(events, list) else [events]
    texts = [
        part["text"]
        for ev in event_list
        if isinstance(ev, dict)
        for part in ((ev.get("content") or {}).get("parts") or [])
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ]
    return "\n".join(texts).strip()


def percentile(sorted_vals: list[float], pct: float) -> float:
    """Returns the nearest-rank `pct`-th percentile from a sorted float list."""
    if not sorted_vals:
        return 0.0
    idx = min(
        len(sorted_vals) - 1,
        max(0, round((pct / 100.0) * (len(sorted_vals) - 1))),
    )
    return sorted_vals[idx]


async def simulate_adk_cloud_run_user(  # pylint: disable=too-many-locals
    client: httpx.AsyncClient,
    target: CloudRunTarget,
    user_id: int,
    semaphore: asyncio.Semaphore,
    delay_s: float,
) -> CloudRunMetric:
    """Creates an isolated ADK session and invokes `POST /run` for one user."""
    if delay_s > 0:
        await asyncio.sleep(delay_s)

    async with semaphore:
        user_str = f"loadtest-user-{user_id}"
        session_id = f"session-{user_id}-{uuid.uuid4().hex[:8]}"
        headers = {"X-Client-Session": f"adk-loadtest-user-{user_id}"}
        if target.bearer_token:
            headers["Authorization"] = f"Bearer {target.bearer_token}"

        t0 = time.perf_counter()
        try:
            sess_url = (
                f"{target.base_url}/apps/{target.app_name}/users/{user_str}/sessions"
            )
            sess_resp = await client.post(
                sess_url, headers=headers, json={"session_id": session_id}
            )
            if sess_resp.status_code not in (_HTTP_OK, 201):
                return CloudRunMetric(
                    user_id,
                    sess_resp.status_code,
                    time.perf_counter() - t0,
                    False,
                    error=(
                        f"Session creation HTTP {sess_resp.status_code}: "
                        f"{sess_resp.text[:140]}"
                    ),
                )
            sess_json = sess_resp.json()
            if isinstance(sess_json, dict) and sess_json.get("id"):
                session_id = sess_json["id"]

            # Forward Cloud Run `--session-affinity` cookies (e.g. `GAESA`) so
            # `/run` hits the exact container that holds the created session.
            run_headers = dict(headers)
            if sess_resp.cookies:
                run_headers["Cookie"] = "; ".join(
                    f"{k}={v}" for k, v in sess_resp.cookies.items()
                )
            payload = {
                "app_name": target.app_name,
                "user_id": user_str,
                "session_id": session_id,
                "new_message": {"role": "user", "parts": [{"text": target.prompt}]},
                "streaming": False,
            }
            resp = await client.post(
                f"{target.base_url}/run", headers=run_headers, json=payload
            )
            elapsed = time.perf_counter() - t0
            if resp.status_code != _HTTP_OK:
                return CloudRunMetric(
                    user_id,
                    resp.status_code,
                    elapsed,
                    False,
                    error=f"HTTP {resp.status_code}: {resp.text[:160]}",
                )
            text = extract_adk_event_text(resp.json())
            return CloudRunMetric(
                user_id,
                _HTTP_OK,
                elapsed,
                bool(text),
                preview=text[:120].replace("\n", " "),
                error="" if text else "Empty ADK /run event text",
            )
        except (httpx.HTTPError, ValueError, OSError) as err:
            return CloudRunMetric(
                user_id, 0, time.perf_counter() - t0, False, error=str(err)[:160]
            )


def _print_summary(
    results: list[CloudRunMetric], users: int, wall_elapsed: float
) -> tuple[int, list[float]]:
    """Prints Cloud Run throughput and latency percentiles."""
    ok = [r for r in results if r.ok]
    lat = sorted(r.latency_s for r in ok)
    print(
        f"\nCLOUD RUN ADK SUMMARY: {len(ok)}/{users} succeeded"
        f" ({(len(ok) / max(1, users)) * 100:.1f}%) in {wall_elapsed:.2f}s"
    )
    print(
        f"  Status Codes : {dict(Counter(r.status_code for r in results))} |"
        f" Throughput: {len(results) / max(0.001, wall_elapsed):.2f} req/s"
    )
    if lat:
        print(
            f"  End-to-End   : Min={lat[0]:.2f}s | Mean={statistics.mean(lat):.2f}s"
            f" | P50={percentile(lat, 50):.2f}s | P90={percentile(lat, 90):.2f}s |"
            f" P95={percentile(lat, 95):.2f}s | Max={lat[-1]:.2f}s"
        )
    if ok:
        print(f'  Sample Reply : "{ok[0].preview}"')
    for err, count in Counter(r.error for r in results if not r.ok).most_common(5):
        print(f"  ERROR ({count}x): {err}")
    return len(ok), lat


async def run_cloud_run_test(  # pylint: disable=too-many-locals
    args: argparse.Namespace,
) -> int:
    """Dispatches concurrent user requests and checks the `--slo-p95` gate."""
    base_url = args.url.rstrip("/")
    limits = httpx.Limits(
        max_connections=max(100, args.concurrency * 2),
        max_keepalive_connections=max(50, args.concurrency),
    )
    headers = (
        {"Authorization": f"Bearer {args.bearer_token}"} if args.bearer_token else {}
    )

    async with httpx.AsyncClient(timeout=args.timeout, limits=limits) as client:
        app_name = args.app_name
        if not app_name:
            apps_resp = await client.get(f"{base_url}/list-apps", headers=headers)
            apps_resp.raise_for_status()
            apps = apps_resp.json()
            app_name = apps[0] if isinstance(apps, list) and apps else "app"
        print(f"Connected to Cloud Run ADK service: app='{app_name}' at {base_url}")

        target = CloudRunTarget(
            base_url=base_url,
            app_name=app_name,
            bearer_token=args.bearer_token,
            prompt=args.prompt,
        )
        semaphore = asyncio.Semaphore(args.concurrency)
        stagger = (
            args.ramp_seconds / (args.users - 1)
            if args.ramp_seconds > 0 and args.users > 1
            else 0.0
        )
        t0 = time.perf_counter()
        results = await asyncio.gather(
            *(
                simulate_adk_cloud_run_user(
                    client=client,
                    target=target,
                    user_id=i + 1,
                    semaphore=semaphore,
                    delay_s=i * stagger,
                )
                for i in range(args.users)
            )
        )
        wall_elapsed = time.perf_counter() - t0

    ok_count, lat = _print_summary(results, args.users, wall_elapsed)
    p95_val = percentile(lat, 95) if lat else float("inf")
    return 0 if (ok_count == args.users and p95_val <= args.slo_p95) else 1


def main() -> int:
    """Parses CLI flags and runs the Cloud Run ADK concurrency gate."""
    parser = argparse.ArgumentParser(
        description="End-to-end concurrency & P95 SLO checker for ADK on Cloud Run."
    )
    parser.add_argument(
        "--url",
        "--host",
        dest="url",
        required=True,
        help="Cloud Run HTTPS URL of the deployed ADK agent.",
    )
    parser.add_argument(
        "--app-name",
        default="",
        help="Optional ADK app name (auto-discovered via GET /list-apps if omitted).",
    )
    parser.add_argument(
        "--bearer-token",
        default=os.environ.get("CLOUD_RUN_ID_TOKEN", ""),
        help="Cloud Run OIDC ID token for IAM-authenticated services.",
    )
    parser.add_argument(
        "--prompt",
        default="How much VRAM does gemma-4-26B-A4B-it in 4bit quantization need?",
    )
    parser.add_argument(
        "--slo-p95",
        type=float,
        default=35.0,
        help="Maximum acceptable end-to-end P95 latency in seconds (default: 35.0).",
    )
    parser.add_argument("--users", type=int, default=5)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--ramp-seconds", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=180.0)
    return asyncio.run(run_cloud_run_test(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
