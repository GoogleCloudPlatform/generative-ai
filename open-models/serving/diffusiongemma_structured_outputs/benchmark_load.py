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

"""High-parallelism async HTTP load-testing engine for DiffusionGemma."""

import asyncio
import concurrent.futures
from datetime import datetime, timezone
import json
import statistics
import time
from typing import Any

import google.auth
import google.auth.transport.requests
from google.cloud import aiplatform
import httpx

import diffusiongemma_client
import run_example


def fetch_gcloud_bearer_token() -> str:
    """Obtains a fresh Google Cloud OAuth2 bearer token from ADC."""
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return str(creds.token)


def build_dedicated_raw_predict_url(endpoint: aiplatform.Endpoint) -> str:
    """Builds the Dedicated Endpoint HTTPS URL for :rawPredict."""
    dns = endpoint.dedicated_endpoint_dns
    if not dns:
        raise RuntimeError(
            f"Endpoint '{endpoint.resource_name}' does not have a dedicated"
            " DNS enabled."
        )
    return f"https://{dns}/v1/{endpoint.resource_name}:rawPredict"


def _compute_percentile(sorted_vals: list[float], pct: float) -> float:
    """Computes a linear-interpolated percentile from a sorted list."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = (pct / 100.0) * (len(sorted_vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = rank - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


async def _post_raw_predict_with_retry(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    payload_bytes: bytes,
    max_retries: int = 3,
) -> tuple[dict[str, Any], float]:
    """Sends an async POST with exponential backoff on transient 429/503s."""
    delay = 0.25
    for attempt in range(max_retries + 1):
        t0 = time.perf_counter()
        resp = await client.post(url, content=payload_bytes, headers=headers)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        if resp.status_code in (429, 502, 503, 504) and attempt < max_retries:
            await asyncio.sleep(delay)
            delay *= 2.0
            continue
        resp.raise_for_status()
        return resp.json(), elapsed_ms
    raise RuntimeError("Unreachable retry state.")


def _run_async(coro: Any) -> Any:
    """Runs an async coroutine in CLI or inside an active Jupyter event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


async def _refresh_bearer_header_async(
    headers: dict[str, str],
    auth_lock: asyncio.Lock,
    auth_state: dict[str, float],
    force: bool = False,
) -> None:
    """Refreshes the OAuth2 bearer token header when expired or forced."""
    async with auth_lock:
        if not force and (time.monotonic() - auth_state["ts"]) < 1200.0:
            return
        fresh = await asyncio.to_thread(fetch_gcloud_bearer_token)
        headers["Authorization"] = f"Bearer {fresh}"
        auth_state["ts"] = time.monotonic()


async def _send_single_payload_async(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    body: bytes,
    sem: asyncio.Semaphore,
    auth_lock: asyncio.Lock,
    auth_state: dict[str, float],
) -> tuple[dict[str, Any] | None, float | None]:
    """Sends one request under the concurrency semaphore, refreshing on 401."""
    async with sem:
        if (time.monotonic() - auth_state["ts"]) >= 1200.0:
            await _refresh_bearer_header_async(
                headers, auth_lock, auth_state, force=False
            )
        try:
            return await _post_raw_predict_with_retry(
                client, url, headers, body
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                try:
                    await _refresh_bearer_header_async(
                        headers, auth_lock, auth_state, force=True
                    )
                    return await _post_raw_predict_with_retry(
                        client, url, headers, body
                    )
                except Exception:
                    return None, None
            return None, None
        except Exception:
            return None, None


async def _execute_concurrent_requests_async(
    url: str,
    token: str,
    payloads: list[bytes],
    concurrency: int,
) -> tuple[list[dict[str, Any] | None], list[float], int]:
    """Executes pre-serialized payloads at the target concurrency level."""
    limits = httpx.Limits(
        max_connections=max(256, concurrency * 2),
        max_keepalive_connections=max(256, concurrency),
        keepalive_expiry=30.0,
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    auth_state = {"ts": time.monotonic()}
    auth_lock = asyncio.Lock()
    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(limits=limits, timeout=60.0) as client:
        # Pre-warm a connection before starting timed requests.
        if payloads:
            try:
                await _post_raw_predict_with_retry(
                    client, url, headers, payloads[0]
                )
            except Exception:
                pass

        outcomes = await asyncio.gather(
            *(
                _send_single_payload_async(
                    client, url, headers, body, sem, auth_lock, auth_state
                )
                for body in payloads
            )
        )

    results = [data for data, _ in outcomes]
    latencies_ms = [ms for _, ms in outcomes if ms is not None]
    errors = sum(1 for data, _ in outcomes if data is None)
    return results, latencies_ms, errors


def _extract_token_metrics(
    responses: list[dict[str, Any] | None],
    fallback_prompt_tokens: int,
    fallback_output_tokens: int,
    wall_sec: float,
) -> dict[str, int | float]:
    """Aggregates prompt, output, and total token counts from vLLM responses."""
    prompt_toks: list[int] = []
    output_toks: list[int] = []
    for resp in responses:
        if not isinstance(resp, dict):
            continue
        usage = resp.get("usage")
        if isinstance(usage, dict) and "prompt_tokens" in usage:
            prompt_toks.append(int(usage.get("prompt_tokens", 0)))
            output_toks.append(
                int(usage.get("completion_tokens", fallback_output_tokens))
            )
        else:
            prompt_toks.append(fallback_prompt_tokens)
            output_toks.append(fallback_output_tokens)

    if not prompt_toks:
        return {
            "prompt_tokens_mean": 0.0,
            "output_tokens_mean": 0.0,
            "total_tokens": 0,
            "tokens_per_s": 0.0,
        }

    total_toks = int(sum(prompt_toks) + sum(output_toks))
    return {
        "prompt_tokens_mean": round(statistics.mean(prompt_toks), 1),
        "output_tokens_mean": round(statistics.mean(output_toks), 1),
        "total_tokens": total_toks,
        "tokens_per_s": round(total_toks / max(1e-6, wall_sec), 1),
    }


def run_concurrency_sweep(
    client: diffusiongemma_client.DiffusionGemmaClient,
    url: str,
    token: str,
    concurrencies: list[int],
    requests_per_level: int,
    model: str,
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    """Runs a parallel load test across concurrency levels (e.g. 1,2,4,8,16)."""
    compiled = client.build_canvas(run_example.EXAMPLE_QUESTIONS)
    sample_req = client.build_request(
        f"request_id: c1-0\n{run_example.EXAMPLE_STATE}",
        compiled,
        model=model,
    )
    fallback_prompt_tokens = len(
        client.tok.encode(
            "\n".join(m["content"] for m in sample_req["messages"]),
            add_special_tokens=False,
        )
    )
    fallback_output_tokens = int(compiled["canvas_width"])

    flat_metrics: dict[str, float] = {}
    table_rows: list[dict[str, Any]] = []

    for c in concurrencies:
        total_reqs = max(requests_per_level, c * 2)
        # Prepend a unique request_id per payload to bypass prefix caching.
        payloads = [
            json.dumps(
                client.build_request(
                    f"request_id: c{c}-{i}\n{run_example.EXAMPLE_STATE}",
                    compiled,
                    model=model,
                )
            ).encode("utf-8")
            for i in range(total_reqs)
        ]
        start_utc = datetime.now(timezone.utc)
        t_start = time.perf_counter()
        responses, latencies_ms, errors = _run_async(
            _execute_concurrent_requests_async(
                url, token, payloads, concurrency=c
            )
        )
        wall_sec = max(1e-6, time.perf_counter() - t_start)
        end_utc = datetime.now(timezone.utc)
        sorted_lat = sorted(latencies_ms)
        rps = len(sorted_lat) / wall_sec
        tok_metrics = _extract_token_metrics(
            responses=responses,
            fallback_prompt_tokens=fallback_prompt_tokens,
            fallback_output_tokens=fallback_output_tokens,
            wall_sec=wall_sec,
        )

        row = {
            "concurrency": c,
            "requests": total_reqs,
            "succeeded": len(sorted_lat),
            "errors": errors,
            "duration_s": round(wall_sec, 1),
            "rps": round(rps, 2),
            **tok_metrics,
            "min_ms": round(sorted_lat[0], 1) if sorted_lat else 0.0,
            "mean_ms": (
                round(statistics.mean(sorted_lat), 1) if sorted_lat else 0.0
            ),
            "p50_ms": round(_compute_percentile(sorted_lat, 50), 1),
            "p90_ms": round(_compute_percentile(sorted_lat, 90), 1),
            "p95_ms": round(_compute_percentile(sorted_lat, 95), 1),
            "p99_ms": round(_compute_percentile(sorted_lat, 99), 1),
            "start_utc": start_utc.isoformat(),
            "end_utc": end_utc.isoformat(),
        }
        table_rows.append(row)
        flat_metrics[f"c{c}_rps"] = row["rps"]
        flat_metrics[f"c{c}_tokens_per_s"] = float(row["tokens_per_s"])
        flat_metrics[f"c{c}_p50_ms"] = row["p50_ms"]
        flat_metrics[f"c{c}_p90_ms"] = row["p90_ms"]
        flat_metrics[f"c{c}_p95_ms"] = row["p95_ms"]
        flat_metrics[f"c{c}_p99_ms"] = row["p99_ms"]
        flat_metrics[f"c{c}_errors"] = float(errors)

    return flat_metrics, table_rows
