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

"""Run an enterprise support triage example on a DiffusionGemma vLLM endpoint.

Usage:
    # Run 3 sequential structured reads (1 cold + 2 warm keep-alive).
    python3 run_example.py --project your-project-id \
        --region us-central1 --runs 3
"""

import argparse
import json
import statistics
import time
from typing import Any

from google.cloud import aiplatform

import config
import diffusiongemma_client

EXAMPLE_STATE = (
    "customer_tier: Enterprise Plus\n"
    "subject: URGENT: Production SSO login failing after cert rotation\n"
    "body: Hi team, after rotating our SAML certificate 20 minutes ago,"
    " none of our 400 engineers can log into the dashboard. We have a"
    " release freeze in 2 hours and if we cannot resolve this today we"
    " will need to pause our upcoming Q4 contract expansion."
)

EXAMPLE_QUESTIONS: dict[str, dict[str, Any]] = {
    "routing_team": {
        "type": "choice",
        "instructions": (
            "Which specialized engineering team should own this ticket?"
        ),
        "criteria": {
            "identity_and_security": (
                "SSO, SAML, OAuth, certificates, authentication, login issues"
            ),
            "billing_and_accounts": (
                "invoices, refunds, payment methods, subscription charges"
            ),
            "core_platform_infra": (
                "database outages, storage corruption, compute provisioning"
            ),
        },
    },
    "severity_level": {
        "type": "score",
        "instructions": "What is the operational severity of this incident?",
        "criteria": [
            "low - general question or minor cosmetic issue",
            "medium - partial feature issue with a workaround",
            "critical - production blocker preventing users from working",
        ],
    },
    "churn_or_expansion_risk": {
        "type": "boolean",
        "instructions": (
            "Is the customer signaling risk to a contract renewal,"
            " expansion, or threatening to cancel?"
        ),
    },
    "requires_immediate_page": {
        "type": "boolean",
        "instructions": (
            "Does this issue block production access and require paging the"
            " on-call engineer immediately?"
        ),
    },
}


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--project", default=config.resolve_default_project())
    ap.add_argument("--region", default=config.REGION)
    ap.add_argument("--endpoint", default=config.ENDPOINT_ID)
    ap.add_argument("--tokenizer", default=config.HF_MODEL_ID)
    ap.add_argument("--served-model-name", default=config.SERVED_MODEL_NAME)
    ap.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of sequential requests (run 1 warmup + N-1 warm)",
    )
    args = ap.parse_args()

    aiplatform.init(project=args.project, location=args.region)
    endpoint = diffusiongemma_client.resolve_endpoint(args.endpoint)

    print(f"Loading tokenizer '{args.tokenizer}' and building canvas...")
    client = diffusiongemma_client.DiffusionGemmaClient(args.tokenizer)
    compiled = client.build_canvas(EXAMPLE_QUESTIONS)
    req_body = client.build_request(
        state=EXAMPLE_STATE,
        compiled=compiled,
        model=args.served_model_name,
    )
    body_bytes = json.dumps(req_body).encode("utf-8")
    print(
        f"Built {len(compiled['slots'])} questions into"
        f" canvas_width={compiled['canvas_width']} tokens"
        f" ({len(compiled['all_label_ids'])} constrained label IDs).\n"
    )

    warm_latencies_ms: list[float] = []
    parsed_result: dict[str, Any] | None = None

    for i in range(1, args.runs + 1):
        label = "cold/warmup" if i == 1 else "warm keep-alive"
        t0 = time.perf_counter()
        raw_resp = endpoint.raw_predict(
            body=body_bytes,
            headers={"Content-Type": "application/json"},
            use_dedicated_endpoint=True,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        raw_resp.raise_for_status()
        parsed_result = client.parse_response(raw_resp.json(), compiled)
        if i > 1 or args.runs == 1:
            warm_latencies_ms.append(elapsed_ms)
        print(
            f"Run {i}/{args.runs} ({label}) | HTTP {raw_resp.status_code} |"
            f" Client Round-Trip: {elapsed_ms:.1f} ms"
        )

    if warm_latencies_ms:
        print(
            "\nWarm Latency Summary:"
            f" min={min(warm_latencies_ms):.1f} ms |"
            f" median={statistics.median(warm_latencies_ms):.1f} ms |"
            f" mean={statistics.mean(warm_latencies_ms):.1f} ms"
        )

    print("\nStructured Diffusion Read Output:")
    print(json.dumps(parsed_result, indent=2))


if __name__ == "__main__":
    main()
