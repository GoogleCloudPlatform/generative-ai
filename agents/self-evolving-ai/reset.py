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

"""Reset utility for Project Chrysalis: Agent Platform Version.

Restores Cloud Memorystore, Cloud SQL pool, telemetry buffers, APEX hotpatches and the
ADK multi-agent topology back to their Day-0 baseline. If the interactive server is
running on port 8009 it is reset via its `/admin/reset` endpoint as well.
"""
import sys
import os

import httpx

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.target_env.server import platform_env  # noqa: E402  # pylint: disable=wrong-import-position
from app.config import SERVER_HOST, SERVER_PORT  # noqa: E402  # pylint: disable=wrong-import-position


def reset_platform_environment() -> None:
    """Reset the in-process platform (and a live server, if running) to the Day-0 baseline."""
    print("\n" + "=" * 88)
    print("   RESETTING PROJECT CHRYSALIS AGENT PLATFORM TO BASELINE")
    print("=" * 88)

    print("\n[1/4] Purging Google Cloud Memorystore & resetting LRU metrics...")
    print("[2/4] Resetting Google Cloud SQL connection pool & unlocking semaphores...")
    print("[3/4] Flushing telemetry, detaching APEX hotpatches, expiring open HITL tickets, forgetting learned principles...")
    platform_env.reset_to_baseline()

    # Notify a live interactive server (uvicorn on port 8009), if one is running.
    base_url = f"http://{SERVER_HOST}:{SERVER_PORT}"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(f"{base_url}/admin/reset")
            if resp.status_code == 200:
                body = resp.json()
                print(f"      Live server at {base_url} notified: {body.get('status')} "
                      f"(expired HITL tickets: {body.get('expired_hitl_tickets', 0)}, "
                      f"forgotten principles: {body.get('forgotten_principles', 0)})")
    except Exception:  # pylint: disable=broad-exception-caught
        pass  # Server not running standalone; in-process reset completed

    print("[4/4] Restoring baseline Google ADK 2.0 Multi-Agent Topology...")
    # The supervisor runner (and its evolved sub-agents) is rebuilt from scratch on next use.
    sub_agent_names = [a.name for a in platform_env.supervisor_runner.supervisor_agent.sub_agents]

    metrics = platform_env.telemetry.get_current_metrics()
    cache_stats = platform_env.cache.get_stats()
    pool_stats = platform_env.db.get_pool_stats()

    print("\n✔ AGENT PLATFORM SUCCESSFULLY RESTORED TO PRISTINE BASELINE:")
    print("-" * 88)
    print("• Target Environment Rate Limiter : None (KMS Hotpatch Detached)")
    print(f"• Memorystore Active Keys / Evicts: {cache_stats['active_keys']} keys / {cache_stats['eviction_count']} evictions")
    print(f"• Cloud SQL Connection Pool       : {pool_stats['active_connections']} / {pool_stats['pool_limit']} active (Unlocked)")
    print(f"• Active ADK Agent Topology       : supervisor_router_agent -> {sub_agent_names} (Baseline 2 Agents)")
    print("• Model Armor & Cloud KMS Guard   : ACTIVE")
    print(f"• P99 Latency / 5xx Error Rate    : {metrics['p99_latency_ms']} ms / {metrics['http_5xx_rate']*100:.1f}%")
    print("-" * 88)
    print("Ready to run fresh demonstration: .venv/bin/python3 demo_runner.py\n")


if __name__ == "__main__":
    reset_platform_environment()
