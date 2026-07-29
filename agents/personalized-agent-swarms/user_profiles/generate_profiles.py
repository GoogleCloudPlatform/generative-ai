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

"""Generate profiles.json with 5 user personas, each with 50 conversation scenarios.

All data is hardcoded for determinism. Run:
    python user_profiles/generate_profiles.py
    python user_profiles/generate_profiles.py --force   # overwrite existing
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def build_profiles() -> dict:
    """Return the complete profiles data structure."""
    profiles = {
        "metadata": {
            "version": "1.0",
            "total_users": 5,
            "scenarios_per_user": 50,
            "total_scenarios": 250,
        },
        "users": [
            _build_user_1(),
            _build_user_2(),
            _build_user_3(),
            _build_user_4(),
            _build_user_5(),
        ],
    }
    return profiles


# ---------------------------------------------------------------------------
# User 1 — Jordan Kim
# ---------------------------------------------------------------------------


def _build_user_1() -> dict:
    return {
        "user_id": "user_1",
        "name": "Jordan Kim",
        "persona": "Senior software engineer, Python + Google Cloud. Terse, wants code examples.",
        "recurring_intents": [
            "debug_python_code",
            "write_unit_tests",
            "deploy_gcp_service",
            "review_pull_request",
            "explain_library_api",
            "optimize_sql_query",
            "write_dockerfile",
            "configure_ci_cd",
            "refactor_legacy_code",
            "troubleshoot_networking",
        ],
        "scenarios": [
            # --- debug_python_code (5) ---
            {
                "scenario_id": "user_1_scenario_001",
                "intent": "debug_python_code",
                "opening_message": "Getting a TypeError: 'NoneType' object is not subscriptable on line 42 of my FastAPI handler. The dict comes back from Redis — any idea why it'd be None?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_002",
                "intent": "debug_python_code",
                "opening_message": "asyncio.gather is swallowing exceptions silently. I have return_exceptions=False but some coroutines just vanish. Python 3.11.",
                "follow_up_strategy": "clarify",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_1_scenario_003",
                "intent": "debug_python_code",
                "opening_message": "Segfault in a Cython extension when calling numpy ufunc on a memoryview. Happens only with arrays > 10M elements.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 5,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_1_scenario_004",
                "intent": "debug_python_code",
                "opening_message": "My Pydantic v2 model validator raises ValidationError on valid input after upgrading from v1. Field is Optional[list[str]].",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_1_scenario_005",
                "intent": "debug_python_code",
                "opening_message": "Circular import between my services/ and models/ packages. Tried TYPE_CHECKING but still breaks at runtime with gunicorn.",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- write_unit_tests (5) ---
            {
                "scenario_id": "user_1_scenario_006",
                "intent": "write_unit_tests",
                "opening_message": "Need pytest tests for a function that retries HTTP calls with exponential backoff. Want to mock time.sleep and httpx.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_007",
                "intent": "write_unit_tests",
                "opening_message": "Write parametrized tests for a date parsing util that handles ISO 8601, Unix timestamps, and relative strings like '3 days ago'.",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_1_scenario_008",
                "intent": "write_unit_tests",
                "opening_message": "How do I test a SQLAlchemy async session with pytest-asyncio? I keep getting event loop errors.",
                "follow_up_strategy": "clarify",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_1_scenario_009",
                "intent": "write_unit_tests",
                "opening_message": "Need a conftest.py fixture that spins up a Firestore emulator, seeds data, and tears down after each test module.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_010",
                "intent": "write_unit_tests",
                "opening_message": "Best way to snapshot-test a CLI tool's stdout/stderr output in pytest?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- deploy_gcp_service (5) ---
            {
                "scenario_id": "user_1_scenario_011",
                "intent": "deploy_gcp_service",
                "opening_message": "Cloud Run cold starts are 8s. Service uses grpcio + protobuf. How do I cut that down?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_012",
                "intent": "deploy_gcp_service",
                "opening_message": "Need a Terraform module for a Cloud Function Gen2 triggered by Pub/Sub with a dead-letter topic.",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_013",
                "intent": "deploy_gcp_service",
                "opening_message": "Getting 403 on Cloud Run even though the invoker SA has roles/run.invoker. Works fine from gcloud but not from the other service.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_1_scenario_014",
                "intent": "deploy_gcp_service",
                "opening_message": "What's the recommended pattern for blue/green deploys on GKE Autopilot with Istio?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_1_scenario_015",
                "intent": "deploy_gcp_service",
                "opening_message": "Need to set up Workload Identity Federation for GitHub Actions deploying to Cloud Run. Show me the gcloud commands.",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- review_pull_request (5) ---
            {
                "scenario_id": "user_1_scenario_016",
                "intent": "review_pull_request",
                "opening_message": "Review this diff — colleague replaced all dict comprehensions with for-loops 'for readability'. 200-line PR. Is this worth pushing back on?",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_1_scenario_017",
                "intent": "review_pull_request",
                "opening_message": "PR adds a global singleton cache with no TTL or size limit. What questions should I raise in the review?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_018",
                "intent": "review_pull_request",
                "opening_message": "Reviewing a PR that uses threading.local() in an async codebase. Is that safe with uvicorn workers?",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_019",
                "intent": "review_pull_request",
                "opening_message": "Junior dev wrote a custom ORM query builder instead of using SQLAlchemy's. It works but I'm worried about SQL injection. How do I frame the feedback?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_1_scenario_020",
                "intent": "review_pull_request",
                "opening_message": "PR swaps requests for httpx across 40 files. Any gotchas I should flag beyond the obvious sync/async differences?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- explain_library_api (5) ---
            {
                "scenario_id": "user_1_scenario_021",
                "intent": "explain_library_api",
                "opening_message": "What's the difference between Depends() and Security() in FastAPI? When would I use one over the other?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_1_scenario_022",
                "intent": "explain_library_api",
                "opening_message": "Explain structlog's BoundLogger vs stdlib logging.Logger. Migrating a large project and need to understand the tradeoffs.",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_023",
                "intent": "explain_library_api",
                "opening_message": "How does Celery's task_acks_late interact with visibility_timeout in Redis broker? Getting duplicate task execution.",
                "follow_up_strategy": "correct",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_1_scenario_024",
                "intent": "explain_library_api",
                "opening_message": "Walk me through Polars lazy vs eager evaluation. When does collect() actually trigger computation?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_025",
                "intent": "explain_library_api",
                "opening_message": "What exactly does anyio.create_task_group() do differently from asyncio.TaskGroup in 3.11?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- optimize_sql_query (5) ---
            {
                "scenario_id": "user_1_scenario_026",
                "intent": "optimize_sql_query",
                "opening_message": "BigQuery query scans 2TB on a 50GB table. It's a JOIN on a partitioned table but I think partition pruning isn't kicking in. Here's the EXPLAIN.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_1_scenario_027",
                "intent": "optimize_sql_query",
                "opening_message": "Postgres query plan shows a seq scan on a 100M row table despite having a B-tree index on the WHERE column. ANALYZE is up to date.",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_028",
                "intent": "optimize_sql_query",
                "opening_message": "Rewrite this N+1 SQLAlchemy ORM query to use a single joined load. It's hitting the DB 500 times per request.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_1_scenario_029",
                "intent": "optimize_sql_query",
                "opening_message": "Need to add a composite index on (tenant_id, created_at, status) — should status be included or is it better as a partial index?",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_030",
                "intent": "optimize_sql_query",
                "opening_message": "Window function ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY ts DESC) is slow on 500M rows. Any alternatives?",
                "follow_up_strategy": "pivot",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- write_dockerfile (5) ---
            {
                "scenario_id": "user_1_scenario_031",
                "intent": "write_dockerfile",
                "opening_message": "Multi-stage Dockerfile for a Python 3.12 FastAPI app with Poetry. Final image should be < 200MB.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_032",
                "intent": "write_dockerfile",
                "opening_message": "Dockerfile for a Rust + Python hybrid service — Rust binary built with cargo, Python scripts use pyo3. How do I layer this?",
                "follow_up_strategy": "clarify",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_1_scenario_033",
                "intent": "write_dockerfile",
                "opening_message": "My Docker build cache invalidates every time requirements.txt changes by one line. How do I use --mount=type=cache for pip?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_1_scenario_034",
                "intent": "write_dockerfile",
                "opening_message": "Need a distroless Python image for Cloud Run. No shell, no package manager, just the app.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_1_scenario_035",
                "intent": "write_dockerfile",
                "opening_message": "Docker Compose setup with hot-reload for a FastAPI backend + React frontend + Postgres + Redis. Dev environment only.",
                "follow_up_strategy": "clarify",
                "max_turns": 5,
                "expected_complexity": "iterative",
            },
            # --- configure_ci_cd (5) ---
            {
                "scenario_id": "user_1_scenario_036",
                "intent": "configure_ci_cd",
                "opening_message": "GitHub Actions workflow: lint, test, build Docker image, push to Artifact Registry, deploy to Cloud Run. Monorepo with 3 services.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_1_scenario_037",
                "intent": "configure_ci_cd",
                "opening_message": "How do I set up matrix builds in GitHub Actions for Python 3.10/3.11/3.12 with different dependency sets?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_1_scenario_038",
                "intent": "configure_ci_cd",
                "opening_message": "CI is taking 25 minutes. Biggest bottleneck is pip install. How do I cache dependencies properly in GitHub Actions?",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_039",
                "intent": "configure_ci_cd",
                "opening_message": "Need a Cloud Build trigger that runs on PR to main, runs tests, and posts the coverage diff as a PR comment.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_040",
                "intent": "configure_ci_cd",
                "opening_message": "Set up Dependabot for Python with auto-merge for patch updates but require review for minor/major.",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- refactor_legacy_code (5) ---
            {
                "scenario_id": "user_1_scenario_041",
                "intent": "refactor_legacy_code",
                "opening_message": "Got a 2000-line views.py in Django. No tests. How do I incrementally break it apart without a big-bang rewrite?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_1_scenario_042",
                "intent": "refactor_legacy_code",
                "opening_message": "Migrating from Flask to FastAPI. The app uses flask.g and before_request hooks heavily. What's the FastAPI equivalent pattern?",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_043",
                "intent": "refactor_legacy_code",
                "opening_message": "Replace all raw string SQL in the codebase with SQLAlchemy Core expressions. About 80 queries across 15 files.",
                "follow_up_strategy": "pivot",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_044",
                "intent": "refactor_legacy_code",
                "opening_message": "This function has 14 boolean parameters. How do I refactor it to use a config dataclass without breaking all callers?",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_1_scenario_045",
                "intent": "refactor_legacy_code",
                "opening_message": "Legacy code uses callbacks everywhere. Want to convert to async/await but can't change the public API yet. Suggestions?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- troubleshoot_networking (5) ---
            {
                "scenario_id": "user_1_scenario_046",
                "intent": "troubleshoot_networking",
                "opening_message": "Intermittent connection reset between two Cloud Run services in the same project. No VPC connector. Happens under load.",
                "follow_up_strategy": "clarify",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_1_scenario_047",
                "intent": "troubleshoot_networking",
                "opening_message": "DNS resolution failing inside a GKE pod for an external API. nslookup works from the node but not the container.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_048",
                "intent": "troubleshoot_networking",
                "opening_message": "mTLS handshake failing between two services with certs generated by cert-manager. Error: certificate verify failed.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_1_scenario_049",
                "intent": "troubleshoot_networking",
                "opening_message": "Cloud NAT external IPs keep rotating and the third-party API has an IP allowlist. How do I pin the egress IP?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_1_scenario_050",
                "intent": "troubleshoot_networking",
                "opening_message": "Load balancer health checks passing but clients get 502s. Backend logs show no errors. Google Cloud HTTPS LB with NEG backend.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 5,
                "expected_complexity": "iterative",
            },
        ],
    }


# ---------------------------------------------------------------------------
# User 2 — Priya Sharma
# ---------------------------------------------------------------------------


def _build_user_2() -> dict:
    return {
        "user_id": "user_2",
        "name": "Priya Sharma",
        "persona": "Marketing manager. Wants structured output with headers.",
        "recurring_intents": [
            "write_campaign_copy",
            "analyze_marketing_metrics",
            "plan_campaign_strategy",
            "create_presentation_outline",
            "conduct_ab_test",
            "write_social_media_posts",
            "analyze_competitor",
            "draft_email_newsletter",
            "create_brand_guidelines",
            "plan_event",
        ],
        "scenarios": [
            # --- write_campaign_copy (5) ---
            {
                "scenario_id": "user_2_scenario_001",
                "intent": "write_campaign_copy",
                "opening_message": "I need copy for a summer product launch — our new line of sustainable water bottles. Target audience is eco-conscious millennials, price point $35. Can you give me headline options and body copy?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_002",
                "intent": "write_campaign_copy",
                "opening_message": "Write a Google Ads headline set (max 30 chars each, 15 headlines) for our B2B SaaS project management tool. Key differentiator: AI-powered sprint planning.",
                "follow_up_strategy": "clarify",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_2_scenario_003",
                "intent": "write_campaign_copy",
                "opening_message": "Need a full-page print ad concept for our organic skincare line launching in Vogue. Luxury positioning, clean beauty angle.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_004",
                "intent": "write_campaign_copy",
                "opening_message": "Quick — need a tagline for our back-to-school campaign. Product: kids' backpacks with built-in GPS trackers. Parents are the buyer, kids are the user.",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_2_scenario_005",
                "intent": "write_campaign_copy",
                "opening_message": "We're launching a loyalty program called 'Inner Circle.' I need the landing page copy — hero section, benefits breakdown, and FAQ section.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- analyze_marketing_metrics (5) ---
            {
                "scenario_id": "user_2_scenario_006",
                "intent": "analyze_marketing_metrics",
                "opening_message": "Our email open rate dropped from 28% to 19% over the last quarter. Unsubscribe rate is steady at 0.4%. What should I investigate first? Here's a breakdown by segment.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_2_scenario_007",
                "intent": "analyze_marketing_metrics",
                "opening_message": "Can you help me build a marketing dashboard KPI framework? We're a D2C e-commerce brand doing $5M ARR. I want to track acquisition, activation, and retention separately.",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_008",
                "intent": "analyze_marketing_metrics",
                "opening_message": "Our CAC went up 40% but LTV only increased 10%. Board meeting in two days. Help me frame this story.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_2_scenario_009",
                "intent": "analyze_marketing_metrics",
                "opening_message": "We spent $50K on Instagram ads last month, $30K on Google, and $20K on TikTok. ROAS is 3.2, 4.8, and 1.1 respectively. How should I reallocate the budget?",
                "follow_up_strategy": "pivot",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_010",
                "intent": "analyze_marketing_metrics",
                "opening_message": "What's a good benchmark for website conversion rate in the luxury fashion e-commerce space? We're at 1.2% and I'm not sure if that's good or bad.",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- plan_campaign_strategy (5) ---
            {
                "scenario_id": "user_2_scenario_011",
                "intent": "plan_campaign_strategy",
                "opening_message": "We're entering the Japanese market with our fitness app. Budget is $200K for the first quarter. Help me plan a go-to-market strategy with channel allocation and milestones.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 5,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_2_scenario_012",
                "intent": "plan_campaign_strategy",
                "opening_message": "Black Friday is 3 months away. Last year we did 2x revenue but margins were thin because of heavy discounting. How do I plan a profitable campaign this year?",
                "follow_up_strategy": "clarify",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_2_scenario_013",
                "intent": "plan_campaign_strategy",
                "opening_message": "Planning a cause marketing campaign partnering with a climate nonprofit. We sell outdoor gear. Give me a 90-day plan.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_014",
                "intent": "plan_campaign_strategy",
                "opening_message": "Our competitor just launched a similar product at a lower price. We need a positioning strategy that doesn't involve a price war. Ideas?",
                "follow_up_strategy": "pivot",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_015",
                "intent": "plan_campaign_strategy",
                "opening_message": "I want to shift our brand from discount-driven to premium positioning. How do I do this gradually without losing our existing customer base?",
                "follow_up_strategy": "correct",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            # --- create_presentation_outline (5) ---
            {
                "scenario_id": "user_2_scenario_016",
                "intent": "create_presentation_outline",
                "opening_message": "Need a 20-slide deck for the quarterly marketing review. Audience is the C-suite. Should cover performance, learnings, and next quarter's plan.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_017",
                "intent": "create_presentation_outline",
                "opening_message": "I'm presenting our influencer marketing results to the CFO. She cares about ROI and unit economics. Help me structure the narrative.",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_2_scenario_018",
                "intent": "create_presentation_outline",
                "opening_message": "Conference talk: 'Why Brand Building Beats Performance Marketing in a Recession.' 30 minutes. Give me an outline with key talking points.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_019",
                "intent": "create_presentation_outline",
                "opening_message": "Pitch deck for getting budget approval for a $500K podcast sponsorship. Need to convince skeptical VPs.",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_2_scenario_020",
                "intent": "create_presentation_outline",
                "opening_message": "Team onboarding presentation: 'How Our Marketing Org Works.' New hire audience. 45 minutes including Q&A.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- conduct_ab_test (5) ---
            {
                "scenario_id": "user_2_scenario_021",
                "intent": "conduct_ab_test",
                "opening_message": "I want to A/B test two checkout page designs. Current conversion is 3.2%, we want to detect a 0.5% lift. How many visitors do I need and for how long?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_022",
                "intent": "conduct_ab_test",
                "opening_message": "Our A/B test shows variant B has 5% higher CTR but 3% lower purchase rate. How do I decide which wins?",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_023",
                "intent": "conduct_ab_test",
                "opening_message": "We want to test subject lines for our weekly newsletter. We have 200K subscribers. What's the best split strategy?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_2_scenario_024",
                "intent": "conduct_ab_test",
                "opening_message": "Is it valid to run an A/B test on pricing? We want to test $29 vs $39 for a digital product. Worried about ethical implications.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_2_scenario_025",
                "intent": "conduct_ab_test",
                "opening_message": "My team keeps peeking at A/B test results early and calling winners at 80% confidence. How do I fix this process?",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- write_social_media_posts (5) ---
            {
                "scenario_id": "user_2_scenario_026",
                "intent": "write_social_media_posts",
                "opening_message": "Write a week of LinkedIn posts for our CEO. She's a fintech founder. Tone: authoritative but approachable. Mix thought leadership with company updates.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_027",
                "intent": "write_social_media_posts",
                "opening_message": "Need 10 Instagram carousel caption ideas for a plant-based protein brand. Target: fitness-conscious Gen Z.",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_2_scenario_028",
                "intent": "write_social_media_posts",
                "opening_message": "We had a product recall and need a transparent social media response. Product: baby food pouches, issue: labeling error (no safety risk). Draft the posts for Twitter, Instagram, and Facebook.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_029",
                "intent": "write_social_media_posts",
                "opening_message": "Create a TikTok content calendar for our coffee brand. 3 posts per week for a month. Mix educational, entertaining, and promotional.",
                "follow_up_strategy": "clarify",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_2_scenario_030",
                "intent": "write_social_media_posts",
                "opening_message": "We're launching a Twitter/X thread series called 'Marketing Myths.' Give me 5 thread outlines that would go viral in the marketing community.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- analyze_competitor (5) ---
            {
                "scenario_id": "user_2_scenario_031",
                "intent": "analyze_competitor",
                "opening_message": "Do a SWOT analysis framework for comparing our email marketing tool against Mailchimp, ConvertKit, and Beehiiv. What dimensions should I evaluate?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_032",
                "intent": "analyze_competitor",
                "opening_message": "Our competitor just raised $50M and is undercutting our pricing by 30%. Help me analyze their likely strategy and our response options.",
                "follow_up_strategy": "clarify",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_2_scenario_033",
                "intent": "analyze_competitor",
                "opening_message": "I need a competitive messaging matrix. Our product vs 3 competitors across 6 feature categories. Give me the template and methodology.",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_2_scenario_034",
                "intent": "analyze_competitor",
                "opening_message": "How do I set up a systematic competitor monitoring process? Currently we're ad-hoc and always surprised by their moves.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_035",
                "intent": "analyze_competitor",
                "opening_message": "Analyze the positioning differences between Notion, Coda, and our tool. We need to find whitespace in the market.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "iterative",
            },
            # --- draft_email_newsletter (5) ---
            {
                "scenario_id": "user_2_scenario_036",
                "intent": "draft_email_newsletter",
                "opening_message": "Draft our monthly product update newsletter. We shipped: dark mode, API v2, and Slack integration. Audience: 15K developers. Keep it concise.",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_2_scenario_037",
                "intent": "draft_email_newsletter",
                "opening_message": "Write a welcome email sequence (5 emails over 14 days) for new subscribers to our parenting blog. Goal: drive them to our paid community.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_2_scenario_038",
                "intent": "draft_email_newsletter",
                "opening_message": "Our win-back email campaign for churned customers isn't working. Current open rate: 12%. Help me rewrite the subject lines and first paragraph.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_039",
                "intent": "draft_email_newsletter",
                "opening_message": "Need a holiday gift guide email for our home decor brand. 20 products, 4 price tiers, 3 recipient categories (for her, for him, for home).",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_2_scenario_040",
                "intent": "draft_email_newsletter",
                "opening_message": "Draft an investor update email. We hit $1M MRR, hired 5 people, and are launching in 2 new markets. Tone: confident but not arrogant.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- create_brand_guidelines (5) ---
            {
                "scenario_id": "user_2_scenario_041",
                "intent": "create_brand_guidelines",
                "opening_message": "We're a health tech startup and don't have brand guidelines yet. Help me create a brand voice document. We want to sound trustworthy, modern, and empathetic.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_2_scenario_042",
                "intent": "create_brand_guidelines",
                "opening_message": "Create a tone-of-voice matrix for different channels: website, email, social media, customer support, and press releases.",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_043",
                "intent": "create_brand_guidelines",
                "opening_message": "Our brand has an inconsistency problem — every team writes differently. Give me a word list of do's and don'ts for our copywriters.",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_2_scenario_044",
                "intent": "create_brand_guidelines",
                "opening_message": "We need to define our brand archetype. We're a premium pet food company that emphasizes science-backed nutrition. Which archetype fits?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_2_scenario_045",
                "intent": "create_brand_guidelines",
                "opening_message": "Write the 'About Us' messaging framework: mission, vision, values, and elevator pitch. We're an edtech company democratizing coding education.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- plan_event (5) ---
            {
                "scenario_id": "user_2_scenario_046",
                "intent": "plan_event",
                "opening_message": "Planning our first annual user conference. Expected 500 attendees, 2-day event, mix of keynotes and workshops. Budget $150K. Give me a planning timeline.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 5,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_2_scenario_047",
                "intent": "plan_event",
                "opening_message": "We want to host a virtual product launch event. 1 hour, live demo + Q&A. How do I maximize attendance and engagement?",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_048",
                "intent": "plan_event",
                "opening_message": "Organizing a VIP dinner for 30 enterprise prospects at a conference. Need the run-of-show, talking points, and follow-up plan.",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_2_scenario_049",
                "intent": "plan_event",
                "opening_message": "Our team hackathon is next month. 60 engineers, 48 hours, themed around AI. Help me plan the logistics, judging criteria, and prizes.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_2_scenario_050",
                "intent": "plan_event",
                "opening_message": "I need a post-event report template for our quarterly webinar series. What metrics should I track and how should I present the ROI?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
        ],
    }


# ---------------------------------------------------------------------------
# User 3 — Alex Chen
# ---------------------------------------------------------------------------


def _build_user_3() -> dict:
    return {
        "user_id": "user_3",
        "name": "Alex Chen",
        "persona": "ML grad student, NLP research. Wants deep technical explanations.",
        "recurring_intents": [
            "explain_research_paper",
            "summarize_ml_concept",
            "help_with_latex",
            "find_datasets",
            "derive_math_proof",
            "compare_model_architectures",
            "debug_training_loop",
            "write_literature_review",
            "explain_statistical_test",
            "design_experiment",
        ],
        "scenarios": [
            # --- explain_research_paper (5) ---
            {
                "scenario_id": "user_3_scenario_001",
                "intent": "explain_research_paper",
                "opening_message": "Can you walk me through the key contributions of 'Attention Is All You Need'? I understand RNNs but the multi-head attention mechanism is unclear to me, especially how Q, K, V matrices interact.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_3_scenario_002",
                "intent": "explain_research_paper",
                "opening_message": "I'm reading the DPO paper (Direct Preference Optimization). How does it eliminate the need for a reward model compared to RLHF? What are the mathematical assumptions?",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_003",
                "intent": "explain_research_paper",
                "opening_message": "Explain the LoRA paper's claim that pretrained weight matrices have low intrinsic rank. Why does this make fine-tuning with low-rank decomposition work?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_004",
                "intent": "explain_research_paper",
                "opening_message": "The FlashAttention paper says it's IO-aware. What does that mean in terms of GPU memory hierarchy, and how does tiling help?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_3_scenario_005",
                "intent": "explain_research_paper",
                "opening_message": "I'm trying to understand the Mixture of Experts paper from Switch Transformers. How does the routing mechanism work, and what's the load balancing loss?",
                "follow_up_strategy": "correct",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            # --- summarize_ml_concept (5) ---
            {
                "scenario_id": "user_3_scenario_006",
                "intent": "summarize_ml_concept",
                "opening_message": "Explain the bias-variance tradeoff in the context of neural networks. Does the classical theory even apply to overparameterized models?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_007",
                "intent": "summarize_ml_concept",
                "opening_message": "What's the intuition behind contrastive learning? I get the idea of pulling positives together, but why does it work without explicit negative mining in newer methods?",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_008",
                "intent": "summarize_ml_concept",
                "opening_message": "Explain tokenization strategies: BPE, WordPiece, Unigram, SentencePiece. When should I use which?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_3_scenario_009",
                "intent": "summarize_ml_concept",
                "opening_message": "I keep seeing 'KL divergence' everywhere in generative modeling. Give me a thorough explanation from information theory basics to its role in VAEs and RLHF.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_3_scenario_010",
                "intent": "summarize_ml_concept",
                "opening_message": "What is the difference between causal, masked, and cross-attention? I mix them up when reading transformer papers.",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- help_with_latex (5) ---
            {
                "scenario_id": "user_3_scenario_011",
                "intent": "help_with_latex",
                "opening_message": "I need a LaTeX template for an ACL 2025 submission. How do I set up the bibliography with natbib and the acl style?",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_3_scenario_012",
                "intent": "help_with_latex",
                "opening_message": "How do I typeset a multi-line equation with aligned equals signs and numbered only the last line? Using amsmath.",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_3_scenario_013",
                "intent": "help_with_latex",
                "opening_message": "My LaTeX table is overflowing the page. It has 8 columns and I need it to fit in a two-column ACL format. What are my options?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_014",
                "intent": "help_with_latex",
                "opening_message": "I want to create a TikZ diagram showing the architecture of my transformer variant — encoder with cross-attention to a knowledge graph. Can you help with the TikZ code?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 5,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_3_scenario_015",
                "intent": "help_with_latex",
                "opening_message": "I need to define custom LaTeX commands for my thesis notation: \\model, \\dataset, \\metric, etc. What's the best practice for organizing these?",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- find_datasets (5) ---
            {
                "scenario_id": "user_3_scenario_016",
                "intent": "find_datasets",
                "opening_message": "I need a multilingual sentiment analysis dataset with at least 10 languages including low-resource ones like Swahili and Bengali. What's available?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_017",
                "intent": "find_datasets",
                "opening_message": "Looking for a large-scale dialogue dataset with annotated discourse relations. Preferably multi-turn and with speaker role labels.",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_018",
                "intent": "find_datasets",
                "opening_message": "What are the standard benchmarks for evaluating text summarization models in 2025? Both extractive and abstractive.",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_3_scenario_019",
                "intent": "find_datasets",
                "opening_message": "I need a dataset of scientific papers with citation contexts annotated by intent (background, method, comparison, etc.). For my citation analysis project.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_3_scenario_020",
                "intent": "find_datasets",
                "opening_message": "Are there any good datasets for code-switching NLP? Specifically English-Hindi or English-Spanish on social media text.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- derive_math_proof (5) ---
            {
                "scenario_id": "user_3_scenario_021",
                "intent": "derive_math_proof",
                "opening_message": "Walk me through the derivation of the ELBO (Evidence Lower Bound) for VAEs. Start from the marginal log-likelihood and show where Jensen's inequality comes in.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_3_scenario_022",
                "intent": "derive_math_proof",
                "opening_message": "Prove that softmax is invariant to constant shifts, i.e., softmax(x + c) = softmax(x). I need this for my paper's appendix.",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_3_scenario_023",
                "intent": "derive_math_proof",
                "opening_message": "Derive the gradient of the cross-entropy loss with respect to the logits, showing why it simplifies to (softmax output - one-hot label).",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_024",
                "intent": "derive_math_proof",
                "opening_message": "I need to show that the KL divergence between two Gaussians has a closed-form solution. Can you derive it step by step?",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_025",
                "intent": "derive_math_proof",
                "opening_message": "Prove that the attention mechanism in transformers is permutation equivariant (ignoring positional encodings). I want to include this in my thesis.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- compare_model_architectures (5) ---
            {
                "scenario_id": "user_3_scenario_026",
                "intent": "compare_model_architectures",
                "opening_message": "Compare Mamba (state space models) vs Transformers for long-sequence modeling. What are the theoretical and practical tradeoffs?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_3_scenario_027",
                "intent": "compare_model_architectures",
                "opening_message": "BERT vs RoBERTa vs DeBERTa for my NER task on biomedical text. Which should I start with and why?",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_3_scenario_028",
                "intent": "compare_model_architectures",
                "opening_message": "What are the key architectural differences between GPT-style decoder-only and T5-style encoder-decoder models? When does each excel?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_029",
                "intent": "compare_model_architectures",
                "opening_message": "Compare the retrieval mechanisms in RAG, REALM, and Atlas. I'm building a retrieval-augmented QA system and need to pick one.",
                "follow_up_strategy": "pivot",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_030",
                "intent": "compare_model_architectures",
                "opening_message": "Adapter layers vs LoRA vs prefix tuning for parameter-efficient fine-tuning. Give me a systematic comparison with complexity analysis.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "iterative",
            },
            # --- debug_training_loop (5) ---
            {
                "scenario_id": "user_3_scenario_031",
                "intent": "debug_training_loop",
                "opening_message": "My loss is NaN after 500 steps. Model is a 125M parameter GPT-2 variant trained with bf16 mixed precision. Learning rate 3e-4 with cosine schedule.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_3_scenario_032",
                "intent": "debug_training_loop",
                "opening_message": "Training loss decreases but validation loss plateaus from epoch 1. Not overfitting because train loss is still high too. Using AdamW with weight decay 0.01.",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_033",
                "intent": "debug_training_loop",
                "opening_message": "My distributed training with DeepSpeed ZeRO-3 is slower than single GPU. 4x A100. What am I doing wrong?",
                "follow_up_strategy": "pivot",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_034",
                "intent": "debug_training_loop",
                "opening_message": "GPU utilization is only 30% during training. I'm using a DataLoader with num_workers=4, pin_memory=True. Batch size 32.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_035",
                "intent": "debug_training_loop",
                "opening_message": "Gradient accumulation is giving different results than large batch training. Using Hugging Face Trainer with gradient_accumulation_steps=8 and per_device_batch_size=4.",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- write_literature_review (5) ---
            {
                "scenario_id": "user_3_scenario_036",
                "intent": "write_literature_review",
                "opening_message": "I need a literature review section on 'hallucination in large language models' for my thesis. Cover detection methods, mitigation strategies, and evaluation benchmarks.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 5,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_3_scenario_037",
                "intent": "write_literature_review",
                "opening_message": "Help me write a 2-page related work section on prompt engineering techniques. I need to organize it thematically, not chronologically.",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_038",
                "intent": "write_literature_review",
                "opening_message": "I'm writing a survey paper on multilingual NLP. Help me categorize the key papers into cross-lingual transfer, multilingual pretraining, and language-specific adaptation.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_3_scenario_039",
                "intent": "write_literature_review",
                "opening_message": "How do I write a good 'gaps in the literature' paragraph that motivates my research question about efficient inference for LLMs?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_3_scenario_040",
                "intent": "write_literature_review",
                "opening_message": "Review my related work paragraph and tell me if I'm being too descriptive vs. analytical. I want to show critical engagement with the prior work.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- explain_statistical_test (5) ---
            {
                "scenario_id": "user_3_scenario_041",
                "intent": "explain_statistical_test",
                "opening_message": "When should I use McNemar's test vs paired bootstrap for comparing two NLP models? My reviewers asked me to justify my choice.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_042",
                "intent": "explain_statistical_test",
                "opening_message": "Explain the Wilcoxon signed-rank test and when it's more appropriate than a paired t-test for comparing model performance across datasets.",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_3_scenario_043",
                "intent": "explain_statistical_test",
                "opening_message": "I ran 5 experiments with different seeds and got F1 scores: 87.2, 86.8, 88.1, 87.5, 86.9. How do I properly report this with confidence intervals?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_3_scenario_044",
                "intent": "explain_statistical_test",
                "opening_message": "What is the Bonferroni correction and when do I need it? I'm comparing my model against 6 baselines on 3 metrics.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_045",
                "intent": "explain_statistical_test",
                "opening_message": "My paper got rejected partly because 'statistical significance is not reported.' How do I add proper significance testing to NLG evaluation metrics like BLEU and ROUGE?",
                "follow_up_strategy": "correct",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            # --- design_experiment (5) ---
            {
                "scenario_id": "user_3_scenario_046",
                "intent": "design_experiment",
                "opening_message": "I want to test whether adding syntactic information improves NER performance on noisy social media text. Help me design the experimental setup, baselines, and ablations.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_3_scenario_047",
                "intent": "design_experiment",
                "opening_message": "How should I design a human evaluation study for comparing summaries from 4 different models? Budget for 200 MTurk annotations.",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_048",
                "intent": "design_experiment",
                "opening_message": "I need to evaluate my model on zero-shot cross-lingual transfer. What languages and datasets should I use to make reviewers happy?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_3_scenario_049",
                "intent": "design_experiment",
                "opening_message": "Design an ablation study for my retrieval-augmented generation model. Components: retriever, reranker, passage fusion, and answer generator.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_3_scenario_050",
                "intent": "design_experiment",
                "opening_message": "How many training examples do I need for few-shot fine-tuning to be statistically meaningful? I'm working with 5 different NLU tasks.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
        ],
    }


# ---------------------------------------------------------------------------
# User 4 — Sam Rivera
# ---------------------------------------------------------------------------


def _build_user_4() -> dict:
    return {
        "user_id": "user_4",
        "name": "Sam Rivera",
        "persona": "Small business owner (cafe). Non-technical, practical.",
        "recurring_intents": [
            "financial_planning",
            "legal_questions",
            "hiring_process",
            "inventory_management",
            "social_media_marketing",
            "customer_feedback",
            "tax_preparation",
            "menu_pricing",
            "supplier_negotiation",
            "business_insurance",
        ],
        "scenarios": [
            # --- financial_planning (5) ---
            {
                "scenario_id": "user_4_scenario_001",
                "intent": "financial_planning",
                "opening_message": "My cafe has been open for 6 months and I'm barely breaking even. Revenue is about $18K/month, rent is $4K, and labor is eating up almost half. How do I figure out where I'm bleeding money?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_4_scenario_002",
                "intent": "financial_planning",
                "opening_message": "I want to open a second location. My current cafe does $25K/month with 15% profit margin. How do I know if I'm ready to expand?",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_003",
                "intent": "financial_planning",
                "opening_message": "What's a good way to forecast my monthly expenses? I've been guessing and I keep getting surprised by things like equipment repairs.",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_4_scenario_004",
                "intent": "financial_planning",
                "opening_message": "Should I take out an SBA loan to buy an espresso machine ($15K) or lease it? My credit score is around 720.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_005",
                "intent": "financial_planning",
                "opening_message": "I need to create a simple P&L statement for my accountant. Never done one before. What categories should I track for a cafe?",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- legal_questions (5) ---
            {
                "scenario_id": "user_4_scenario_006",
                "intent": "legal_questions",
                "opening_message": "A customer slipped on a wet floor and is threatening to sue. I had a wet floor sign up. What should I do right now?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_007",
                "intent": "legal_questions",
                "opening_message": "Do I need a different business license to start selling packaged baked goods for retail, not just in-store consumption?",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_4_scenario_008",
                "intent": "legal_questions",
                "opening_message": "My landlord wants to increase rent by 20% when the lease renews in 3 months. Is there anything I can do? I'm in California.",
                "follow_up_strategy": "pivot",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_009",
                "intent": "legal_questions",
                "opening_message": "An employee posted a negative TikTok about our cafe while wearing their work apron. Can I fire them for that?",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_010",
                "intent": "legal_questions",
                "opening_message": "I want to start a loyalty program where customers earn points. Are there any legal requirements I should know about? Like do I need terms and conditions?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- hiring_process (5) ---
            {
                "scenario_id": "user_4_scenario_011",
                "intent": "hiring_process",
                "opening_message": "I need to hire my first employee. I've been doing everything myself for 4 months. What do I need to set up legally before I can bring someone on?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_4_scenario_012",
                "intent": "hiring_process",
                "opening_message": "What questions can and can't I ask during an interview for a barista position? I don't want to get in trouble.",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_4_scenario_013",
                "intent": "hiring_process",
                "opening_message": "Should I hire part-time baristas or one full-time person? I need coverage from 6am to 3pm, 7 days a week.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_014",
                "intent": "hiring_process",
                "opening_message": "My best barista wants a raise. She's been here 8 months and is asking for $20/hr, up from $17. I can't really afford it but I can't lose her. What do I do?",
                "follow_up_strategy": "pivot",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_015",
                "intent": "hiring_process",
                "opening_message": "How do I write a good job description for a cafe manager? I want someone who can handle opening, inventory, and light bookkeeping.",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- inventory_management (5) ---
            {
                "scenario_id": "user_4_scenario_016",
                "intent": "inventory_management",
                "opening_message": "I'm throwing away too much food at the end of the day, especially pastries. Some days I run out by noon, other days I have 20 left at closing. How do I get this right?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_017",
                "intent": "inventory_management",
                "opening_message": "What's a simple system for tracking coffee bean inventory? I'm using a notebook right now and I keep running out of our most popular blend.",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_4_scenario_018",
                "intent": "inventory_management",
                "opening_message": "My milk costs have gone up 25% in 3 months. Should I switch suppliers, change my menu, or raise prices? I go through about 50 gallons a week.",
                "follow_up_strategy": "pivot",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_019",
                "intent": "inventory_management",
                "opening_message": "I want to set up a par level system for my cafe. What items should I track and what's a reasonable par level for a shop that does 200 drinks a day?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_4_scenario_020",
                "intent": "inventory_management",
                "opening_message": "Is it worth investing in a POS system that tracks inventory automatically? I'm looking at Square vs Toast. Budget is tight.",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- social_media_marketing (5) ---
            {
                "scenario_id": "user_4_scenario_021",
                "intent": "social_media_marketing",
                "opening_message": "I know I should be on Instagram but I have no idea what to post. I'm a cafe, not a photographer. Give me a realistic content plan I can do myself.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_022",
                "intent": "social_media_marketing",
                "opening_message": "Should I pay a local influencer $500 to post about my cafe? She has 15K followers in our city. Is that worth it?",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_4_scenario_023",
                "intent": "social_media_marketing",
                "opening_message": "Got a bad Google review — 1 star, says our coffee is overpriced and the barista was rude. I know exactly who wrote it and they were the rude one. How do I respond?",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_4_scenario_024",
                "intent": "social_media_marketing",
                "opening_message": "I want to run a 'bring a friend, get a free drink' promotion on social media. How do I set this up so people don't abuse it?",
                "follow_up_strategy": "pivot",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_025",
                "intent": "social_media_marketing",
                "opening_message": "My competitor across the street has 3x our Instagram followers and they just opened 6 months ago. What are they probably doing that I'm not?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            # --- customer_feedback (5) ---
            {
                "scenario_id": "user_4_scenario_026",
                "intent": "customer_feedback",
                "opening_message": "I want to start collecting customer feedback but I don't want to be annoying about it. What's the least intrusive way to do this for a cafe?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_4_scenario_027",
                "intent": "customer_feedback",
                "opening_message": "I got feedback that our wifi is too slow and people are leaving because of it. Upgrading the internet plan costs $100 more per month. Is it worth it?",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_028",
                "intent": "customer_feedback",
                "opening_message": "Several regulars have mentioned they wish we had more seating. I physically cannot add more tables. What are creative solutions?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_4_scenario_029",
                "intent": "customer_feedback",
                "opening_message": "My Yelp rating dropped from 4.5 to 4.1 over the last 2 months. I think it's because of one bad employee who I've since let go. How do I recover?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_030",
                "intent": "customer_feedback",
                "opening_message": "A regular customer gave me a whole list of suggestions — new menu items, different music, opening earlier. She means well but it's overwhelming. How do I prioritize?",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- tax_preparation (5) ---
            {
                "scenario_id": "user_4_scenario_031",
                "intent": "tax_preparation",
                "opening_message": "This is my first year filing taxes as a business owner. I'm an LLC taxed as a sole prop. What records do I need to have ready for my accountant?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_032",
                "intent": "tax_preparation",
                "opening_message": "Can I deduct the cost of the espresso machine I bought? What about the build-out costs for the cafe space? How does depreciation work?",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_033",
                "intent": "tax_preparation",
                "opening_message": "I've been paying my baristas in cash and I'm worried I messed up the tax side. What do I need to fix before tax season?",
                "follow_up_strategy": "correct",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_4_scenario_034",
                "intent": "tax_preparation",
                "opening_message": "Do I need to collect sales tax on coffee drinks? What about packaged beans sold for home use? I'm in Texas.",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_4_scenario_035",
                "intent": "tax_preparation",
                "opening_message": "My quarterly estimated tax payment is due next week and I have no idea how much to pay. Revenue was $60K this quarter.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- menu_pricing (5) ---
            {
                "scenario_id": "user_4_scenario_036",
                "intent": "menu_pricing",
                "opening_message": "How do I figure out the right price for a latte? My ingredient cost is about $1.20. I'm charging $5 but the shop next door charges $6.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_037",
                "intent": "menu_pricing",
                "opening_message": "I want to add avocado toast to the menu. How do I price it when avocado prices fluctuate so much? Some weeks my cost doubles.",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_4_scenario_038",
                "intent": "menu_pricing",
                "opening_message": "Should I do dynamic pricing — like cheaper coffee before 8am when we're slow? Or does that confuse customers?",
                "follow_up_strategy": "pivot",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_039",
                "intent": "menu_pricing",
                "opening_message": "I need to raise prices by about 10% due to costs but I'm scared of losing customers. What's the best way to do this?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_4_scenario_040",
                "intent": "menu_pricing",
                "opening_message": "Is it better to have a simple menu with 15 items or a bigger menu with 30? I feel like I'm spreading myself too thin.",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- supplier_negotiation (5) ---
            {
                "scenario_id": "user_4_scenario_041",
                "intent": "supplier_negotiation",
                "opening_message": "My coffee bean supplier just raised prices by 15%. I've been with them for a year. How do I negotiate this or should I switch?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_042",
                "intent": "supplier_negotiation",
                "opening_message": "I want to switch from a big distributor to buying direct from a local bakery for our pastries. How do I approach them about wholesale pricing?",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_4_scenario_043",
                "intent": "supplier_negotiation",
                "opening_message": "A new dairy supplier is offering 20% lower prices if I sign a 2-year contract. Current supplier has been reliable for a year. Worth the risk?",
                "follow_up_strategy": "pivot",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_044",
                "intent": "supplier_negotiation",
                "opening_message": "My supplier keeps delivering late and it messes up my morning prep. I've complained twice. What leverage do I have?",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_045",
                "intent": "supplier_negotiation",
                "opening_message": "Is it worth joining a buying cooperative with other local cafes to get better supplier pricing? How does that typically work?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            # --- business_insurance (5) ---
            {
                "scenario_id": "user_4_scenario_046",
                "intent": "business_insurance",
                "opening_message": "What types of insurance do I actually need for a cafe? I have general liability but my landlord is saying I need more. I don't want to overpay.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_047",
                "intent": "business_insurance",
                "opening_message": "An insurance agent is quoting me $3,500/year for a BOP (business owner's policy). Is that reasonable for a small cafe?",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_4_scenario_048",
                "intent": "business_insurance",
                "opening_message": "Do I need workers' comp insurance if I only have 2 part-time employees? I'm in Florida.",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_4_scenario_049",
                "intent": "business_insurance",
                "opening_message": "My pipe burst over the weekend and damaged some equipment. Does my business insurance cover this? I have a BOP.",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_4_scenario_050",
                "intent": "business_insurance",
                "opening_message": "I want to start offering catering. Do I need additional insurance for that? I'd be preparing food off-site at client locations.",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
        ],
    }


# ---------------------------------------------------------------------------
# User 5 — Maya Tanaka
# ---------------------------------------------------------------------------


def _build_user_5() -> dict:
    return {
        "user_id": "user_5",
        "name": "Maya Tanaka",
        "persona": "Travel enthusiast + home cook. Casual, likes lists.",
        "recurring_intents": [
            "plan_trip",
            "find_recipe",
            "compare_products",
            "learn_japanese",
            "budget_travel",
            "meal_prep",
            "wine_pairing",
            "restaurant_recommendations",
            "travel_packing",
            "cultural_etiquette",
        ],
        "scenarios": [
            # --- plan_trip (5) ---
            {
                "scenario_id": "user_5_scenario_001",
                "intent": "plan_trip",
                "opening_message": "ok so I have 10 days off in September and I'm torn between Portugal and Croatia. I love beaches, good food, and walkable old towns. which one should I pick and what's a rough itinerary?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_5_scenario_002",
                "intent": "plan_trip",
                "opening_message": "planning a solo trip to Japan! 2 weeks, hitting Tokyo, Kyoto, and Osaka for sure. but I also want somewhere off the beaten path — maybe a rural onsen town? help me plan this out",
                "follow_up_strategy": "clarify",
                "max_turns": 5,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_5_scenario_003",
                "intent": "plan_trip",
                "opening_message": "weekend trip from NYC — somewhere within a 3-hour drive, not the Hamptons. ideally cute small town vibes with good restaurants. suggestions?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_004",
                "intent": "plan_trip",
                "opening_message": "my parents want to visit from Japan and I need to plan a week in San Francisco for them. they're in their 60s, love gardens and seafood, and don't walk super fast. what should we do?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_5_scenario_005",
                "intent": "plan_trip",
                "opening_message": "road trip! LA to Seattle along the coast. 7 days. where should I stop and what should I eat? I drive a Prius so gas budget is manageable",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- find_recipe (5) ---
            {
                "scenario_id": "user_5_scenario_006",
                "intent": "find_recipe",
                "opening_message": "I have a bunch of leftover roast chicken, half a butternut squash, and some sage. what can I make that isn't soup?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_007",
                "intent": "find_recipe",
                "opening_message": "trying to make legit tonkotsu ramen at home. I know the broth takes forever but I want the real deal. walk me through it?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_5_scenario_008",
                "intent": "find_recipe",
                "opening_message": "need a showstopper dessert for a dinner party, 8 people. something I can mostly make ahead. I'm pretty comfortable with pastry but not a pro",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_5_scenario_009",
                "intent": "find_recipe",
                "opening_message": "what's a good weeknight pasta that's NOT aglio e olio or cacio e pepe? I've been making those on repeat and need something new. max 30 min",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_010",
                "intent": "find_recipe",
                "opening_message": "my friend is vegan and coming for dinner saturday. I want to make something impressive, not just a salad. she loves Thai food. ideas?",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- compare_products (5) ---
            {
                "scenario_id": "user_5_scenario_011",
                "intent": "compare_products",
                "opening_message": "looking at stand mixers — KitchenAid Artisan vs Cuisinart Precision Master vs Ankarsrum. I bake bread every weekend so I need something that handles heavy dough. which one?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_5_scenario_012",
                "intent": "compare_products",
                "opening_message": "need a good carry-on suitcase. been looking at Away, Monos, and Rimowa. I fly like 10 times a year, mostly domestic. is the Rimowa worth 3x the price?",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_013",
                "intent": "compare_products",
                "opening_message": "should I get a Dutch oven from Le Creuset, Staub, or Lodge? I mostly make stews, braises, and no-knead bread. the price differences are wild",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_014",
                "intent": "compare_products",
                "opening_message": "comparing travel credit cards: Chase Sapphire Reserve vs Amex Gold vs Capital One Venture X. I spend most on dining and flights. which one makes sense?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_5_scenario_015",
                "intent": "compare_products",
                "opening_message": "I want a Japanese knife for home cooking. looking at Tojiro DP vs Miyabi Kaizen vs MAC Professional. mainly for vegetables and boneless proteins. help me decide?",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- learn_japanese (5) ---
            {
                "scenario_id": "user_5_scenario_016",
                "intent": "learn_japanese",
                "opening_message": "I know conversational Japanese from my parents but I can barely read. how should I approach learning kanji as an adult? I know hiragana and katakana already",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_5_scenario_017",
                "intent": "learn_japanese",
                "opening_message": "what's the difference between は and が? I've read like 5 explanations and I still mess it up. can you give me examples that actually make it click?",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_5_scenario_018",
                "intent": "learn_japanese",
                "opening_message": "can you help me practice ordering food in Japanese? like at a regular izakaya, not a fancy place. I want to sound natural, not textbook-y",
                "follow_up_strategy": "pivot",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_5_scenario_019",
                "intent": "learn_japanese",
                "opening_message": "what are some good Japanese podcasts or YouTube channels for intermediate learners? I can follow daily conversation but news Japanese is too hard",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_020",
                "intent": "learn_japanese",
                "opening_message": "help me understand keigo (polite Japanese). when do I use です/ます vs the more formal forms? I'm visiting my grandma's friends in Nagoya and want to be respectful",
                "follow_up_strategy": "correct",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            # --- budget_travel (5) ---
            {
                "scenario_id": "user_5_scenario_021",
                "intent": "budget_travel",
                "opening_message": "going to Thailand for 2 weeks on a budget. like $50/day budget not including flights. is that doable? give me a breakdown of what I'd spend on what",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_5_scenario_022",
                "intent": "budget_travel",
                "opening_message": "what are the best budget airlines in Europe? I'm doing a 3-week trip hitting 5 countries and train tickets are adding up fast",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_023",
                "intent": "budget_travel",
                "opening_message": "is it actually cheaper to book flights on Tuesdays? what are the real tricks for finding cheap flights that actually work in 2026?",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_024",
                "intent": "budget_travel",
                "opening_message": "I want to do a month in Mexico City on a remote work setup. how much should I budget total? need decent wifi and a safe neighborhood",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_5_scenario_025",
                "intent": "budget_travel",
                "opening_message": "hostels vs Airbnb vs budget hotels — which is actually the best value? I'm 28, fine with shared spaces but I need decent sleep",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- meal_prep (5) ---
            {
                "scenario_id": "user_5_scenario_026",
                "intent": "meal_prep",
                "opening_message": "I want to meal prep lunches for the whole work week. I get bored of eating the same thing though. give me 5 different lunches I can prep on Sunday that aren't sad desk food",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_5_scenario_027",
                "intent": "meal_prep",
                "opening_message": "what proteins actually reheat well? I'm tired of rubbery chicken. need options for meal prep that taste good on day 4",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_028",
                "intent": "meal_prep",
                "opening_message": "can you help me plan a week of freezer meals? I'm going to be slammed at work for the next month and I want to batch-cook a bunch of stuff this weekend",
                "follow_up_strategy": "clarify",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_5_scenario_029",
                "intent": "meal_prep",
                "opening_message": "what are some good grab-and-go breakfast options I can prep ahead? I have exactly zero time in the morning. bonus if they're high protein",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_030",
                "intent": "meal_prep",
                "opening_message": "I want to start making my own sauces and dressings in bulk instead of buying bottled ones. give me 5 versatile ones that last at least a week in the fridge",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- wine_pairing (5) ---
            {
                "scenario_id": "user_5_scenario_031",
                "intent": "wine_pairing",
                "opening_message": "making homemade pasta with a mushroom cream sauce tonight. what wine should I pair with it? I prefer not-too-heavy whites but I'm open to light reds",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_032",
                "intent": "wine_pairing",
                "opening_message": "hosting a dinner party — appetizer is bruschetta, main is braised short ribs, dessert is dark chocolate tart. do I need a different wine for each course or can I get away with one or two?",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_5_scenario_033",
                "intent": "wine_pairing",
                "opening_message": "I love sake but don't know anything about it. what are the main types and what foods go with each? I eat a lot of sushi and grilled fish",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_5_scenario_034",
                "intent": "wine_pairing",
                "opening_message": "is there a good wine that goes with spicy Thai food? or is beer just the better call? making pad kra pao tonight",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_035",
                "intent": "wine_pairing",
                "opening_message": "I want to learn more about natural wines. what should I know? my local wine shop has a huge natural section and I've been grabbing random bottles",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- restaurant_recommendations (5) ---
            {
                "scenario_id": "user_5_scenario_036",
                "intent": "restaurant_recommendations",
                "opening_message": "going to Paris for 5 days and I want to eat SO well. mix of fancy and casual. I love bistro food, natural wine bars, and pastries. give me a list!",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_5_scenario_037",
                "intent": "restaurant_recommendations",
                "opening_message": "best ramen in NYC? I've done Ippudo and Ivan Ramen. looking for something more under-the-radar. I like rich tonkotsu and spicy miso styles",
                "follow_up_strategy": "clarify",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_038",
                "intent": "restaurant_recommendations",
                "opening_message": "date night in Chicago — somewhere special but not pretentious. good cocktails a plus. budget around $150 for two including drinks",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_039",
                "intent": "restaurant_recommendations",
                "opening_message": "I'm going to Mexico City and I want to eat like a local. street food, markets, hole-in-the-wall places. give me a food crawl itinerary for Roma and Condesa neighborhoods",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_5_scenario_040",
                "intent": "restaurant_recommendations",
                "opening_message": "what are the best food halls in London? I'll be there for a week and I love trying lots of different things in one place",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            # --- travel_packing (5) ---
            {
                "scenario_id": "user_5_scenario_041",
                "intent": "travel_packing",
                "opening_message": "help me pack for 2 weeks in Southeast Asia with just a carry-on. it'll be hot and humid, I'll be doing temples and beaches and some nice dinners. I'm a light packer but 2 weeks is pushing it",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_5_scenario_042",
                "intent": "travel_packing",
                "opening_message": "what are the travel essentials that people always forget? I'm making my ultimate packing checklist",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_043",
                "intent": "travel_packing",
                "opening_message": "packing for Iceland in November. I know it's going to be cold and wet but I also don't want to check a bag. what layers should I bring?",
                "follow_up_strategy": "clarify",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_5_scenario_044",
                "intent": "travel_packing",
                "opening_message": "what's the best way to organize a suitcase? I've seen packing cubes, compression bags, the rolling method. what actually works?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_045",
                "intent": "travel_packing",
                "opening_message": "I need a good toiletry setup for long trips that meets TSA requirements. I'm picky about skincare and can't just use hotel products",
                "follow_up_strategy": "correct",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            # --- cultural_etiquette (5) ---
            {
                "scenario_id": "user_5_scenario_046",
                "intent": "cultural_etiquette",
                "opening_message": "I'm going to Morocco next month. what cultural stuff should I know? I'm a woman traveling solo and I want to be respectful. tips on dress code, behavior in mosques, tipping?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 3,
                "expected_complexity": "multi_step",
            },
            {
                "scenario_id": "user_5_scenario_047",
                "intent": "cultural_etiquette",
                "opening_message": "visiting my Japanese grandma's hometown for the first time. I'm half Japanese but grew up in the US. what are the social norms I should know about that might be different from what I'm used to?",
                "follow_up_strategy": "clarify",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_5_scenario_048",
                "intent": "cultural_etiquette",
                "opening_message": "what's the tipping culture like across Europe? I never know when to tip and how much. going to France, Italy, Spain, and Portugal",
                "follow_up_strategy": "pivot",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
            {
                "scenario_id": "user_5_scenario_049",
                "intent": "cultural_etiquette",
                "opening_message": "going to India for a friend's wedding. I've never been to an Indian wedding before. what should I wear, bring as a gift, and know about the ceremony?",
                "follow_up_strategy": "deep_dive",
                "max_turns": 4,
                "expected_complexity": "iterative",
            },
            {
                "scenario_id": "user_5_scenario_050",
                "intent": "cultural_etiquette",
                "opening_message": "what are the dining etiquette basics in South Korea? I know you pour drinks for others but there's more to it right? going to Seoul next month",
                "follow_up_strategy": "correct",
                "max_turns": 2,
                "expected_complexity": "simple",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def print_summary(profiles: dict) -> None:
    """Print summary statistics."""
    print("=" * 60)
    print("PROFILES SUMMARY")
    print("=" * 60)
    print(f"Total users:     {profiles['metadata']['total_users']}")
    print(f"Total scenarios: {profiles['metadata']['total_scenarios']}")
    print()

    for user in profiles["users"]:
        scenarios = user["scenarios"]
        print(f"--- {user['user_id']}: {user['name']} ---")
        print(f"  Scenarios: {len(scenarios)}")

        # Intent distribution
        intent_counts = Counter(s["intent"] for s in scenarios)
        print(f"  Intents ({len(intent_counts)} unique):")
        for intent, count in sorted(intent_counts.items()):
            print(f"    {intent}: {count}")

        # Follow-up strategy distribution
        strategy_counts = Counter(s["follow_up_strategy"] for s in scenarios)
        print(f"  Follow-up strategies: {dict(strategy_counts)}")

        # Max turns distribution
        turns_counts = Counter(s["max_turns"] for s in scenarios)
        print(f"  Max turns distribution: {dict(sorted(turns_counts.items()))}")

        # Complexity distribution
        complexity_counts = Counter(s["expected_complexity"] for s in scenarios)
        print(f"  Complexity: {dict(complexity_counts)}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate user profiles for conversation scenarios."
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing profiles.json"
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    output_path = script_dir / "profiles.json"

    if output_path.exists() and not args.force:
        print(f"profiles.json already exists at {output_path}")
        print("Use --force to overwrite.")
        sys.exit(0)

    profiles = build_profiles()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)

    print(f"Generated {output_path}")
    print()
    print_summary(profiles)


if __name__ == "__main__":
    main()
