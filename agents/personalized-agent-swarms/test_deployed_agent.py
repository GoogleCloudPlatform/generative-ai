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

"""Test suite for the deployed User Assistant Agent on Agent Engine.

Usage:
    python test_deployed_agent.py              # Run all tests (keyword checks only)
    python test_deployed_agent.py --verbose    # Show full agent responses
    python test_deployed_agent.py --judge      # Run keyword tests + LLM-as-judge evaluation
    python test_deployed_agent.py --single     # Run only single-turn tests
    python test_deployed_agent.py --multi      # Run only multi-turn tests

All runs save a full JSON report to evaluation_output/<datetime>.json containing
inputs, outputs, keyword results, and (if --judge) LLM judge scores.

Environment variables:
    AGENT_ENGINE_ID   — Override the default Agent Engine resource name
    GOOGLE_CLOUD_PROJECT — Override the Google Cloud project
    GOOGLE_CLOUD_LOCATION — Override the region (default: us-central1)
"""

import argparse
import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import vertexai

# ── Defaults ────────────────────────────────────────────────────────────────

DEFAULT_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
DEFAULT_LOCATION = "us-central1"
DEFAULT_AGENT_ENGINE_ID = os.environ.get(
    "AGENT_ENGINE_ID",
    "projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID",
)
JUDGE_MODEL = "gemini-2.5-pro"
RUBRIC_PATH = Path(__file__).parent / "evaluation_rubric.md"
OUTPUT_DIR = Path(__file__).parent / "evaluation_output"

# ── ANSI colours ────────────────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# ── Dimension display names ────────────────────────────────────────────────

DIMENSION_LABELS = {
    "accuracy": "Accuracy",
    "helpfulness": "Helpfulness",
    "source_usage": "Source Usage",
    "clarity": "Clarity",
    "conciseness": "Conciseness",
    "tone": "Tone",
    "multi_part_handling": "Multi-Part",
    "multilingual_support": "Multilingual",
}


# ── Data structures ────────────────────────────────────────────────────────


@dataclass
class SingleTurnTest:
    name: str
    user_message: str
    expected_keywords: list[str]
    negative_keywords: list[str] = field(default_factory=list)


@dataclass
class Turn:
    user_message: str
    expected_keywords: list[str]
    negative_keywords: list[str] = field(default_factory=list)


@dataclass
class MultiTurnTest:
    name: str
    turns: list[Turn]


@dataclass
class ConversationLog:
    name: str
    test_type: str  # "single_turn" or "multi_turn"
    turns: list[dict]  # [{"role": "user"|"agent", "content": "..."}]
    keyword_checks: list[dict]  # [{"expected_keywords": [...], "passed": bool}]


# ── Single-turn test cases ─────────────────────────────────────────────────

SINGLE_TURN_TESTS: list[SingleTurnTest] = [
    # ── Factual / knowledge questions ──────────────────────────────────
    SingleTurnTest(
        name="Science — photosynthesis explanation",
        user_message="What is photosynthesis?",
        expected_keywords=["sunlight", "carbon dioxide", "oxygen", "plant"],
    ),
    SingleTurnTest(
        name="History — Moon landing",
        user_message="When did humans first land on the Moon?",
        expected_keywords=["1969", "apollo", "neil armstrong"],
    ),
    SingleTurnTest(
        name="Geography — longest river",
        user_message="What is the longest river in the world?",
        expected_keywords=["nile", "amazon"],
    ),
    SingleTurnTest(
        name="Math — basic calculation",
        user_message="What is 17 times 23?",
        expected_keywords=["391"],
    ),
    SingleTurnTest(
        name="Definition — what is GDP",
        user_message="What does GDP stand for and what does it measure?",
        expected_keywords=["gross domestic product"],
    ),
    # ── Current events / web search needed ─────────────────────────────
    SingleTurnTest(
        name="Current events — recent news (web search)",
        user_message="What are the top news stories today?",
        expected_keywords=["news", "today"],
    ),
    SingleTurnTest(
        name="Weather — current conditions (web search)",
        user_message="What's the weather like in Sydney right now?",
        expected_keywords=["sydney", "weather"],
    ),
    SingleTurnTest(
        name="Sports — latest results (web search)",
        user_message="Who won the most recent FIFA World Cup?",
        expected_keywords=["world cup"],
    ),
    # ── How-to / practical questions ───────────────────────────────────
    SingleTurnTest(
        name="How-to — cooking",
        user_message="How do I boil an egg so the yolk is still soft?",
        expected_keywords=["minutes", "water", "boil"],
    ),
    SingleTurnTest(
        name="How-to — tech",
        user_message="How do I take a screenshot on a Mac?",
        expected_keywords=["command", "shift", "screenshot"],
    ),
    # ── Creative / writing ─────────────────────────────────────────────
    SingleTurnTest(
        name="Creative — haiku",
        user_message="Write me a haiku about the ocean",
        expected_keywords=[
            "ocean",
            "wave",
            "sea",
            "water",
            "shore",
            "tide",
            "deep",
            "blue",
            "salt",
        ],
    ),
    SingleTurnTest(
        name="Summarisation — explain like I'm 5",
        user_message="Explain quantum computing like I'm 5 years old",
        expected_keywords=["computer", "fast", "problem"],
    ),
    # ── Disambiguation ─────────────────────────────────────────────────
    SingleTurnTest(
        name="Disambiguation — ambiguous query",
        user_message="Tell me about Mercury",
        expected_keywords=["planet", "element", "?"],
    ),
    # ── Multi-part ─────────────────────────────────────────────────────
    SingleTurnTest(
        name="Multi-part — capital + population",
        user_message="What is the capital of Japan and roughly how many people live there?",
        expected_keywords=["tokyo", "million"],
    ),
    # ── Multilingual ───────────────────────────────────────────────────
    SingleTurnTest(
        name="Multilingual — Spanish greeting",
        user_message="Hola, dime la capital de Francia.",
        expected_keywords=["París", "paris"],
    ),
]

# ── Multi-turn test cases ──────────────────────────────────────────────────

MULTI_TURN_TESTS: list[MultiTurnTest] = [
    MultiTurnTest(
        name="Scenario 1: Follow-up clarification",
        turns=[
            Turn(
                user_message="What's the tallest mountain in the world?",
                expected_keywords=["everest"],
            ),
            Turn(
                user_message="How tall is it exactly?",
                expected_keywords=["8,84", "8848", "8849", "29,03"],
            ),
            Turn(
                user_message="Has anyone died trying to climb it?",
                expected_keywords=["death", "died", "climber"],
            ),
        ],
    ),
    MultiTurnTest(
        name="Scenario 2: Topic deep-dive with web search",
        turns=[
            Turn(
                user_message="What is the James Webb Space Telescope?",
                expected_keywords=["space", "telescope", "nasa", "infrared"],
            ),
            Turn(
                user_message="What are some of its most important discoveries so far?",
                expected_keywords=["discover", "galaxy", "image", "star"],
            ),
        ],
    ),
    MultiTurnTest(
        name="Scenario 3: Multi-topic conversation",
        turns=[
            Turn(
                user_message="What's a good recipe for pancakes?",
                expected_keywords=["flour", "egg", "milk", "pan"],
            ),
            Turn(
                user_message=(
                    "Thanks! Completely different topic — can you explain "
                    "what blockchain is in simple terms?"
                ),
                expected_keywords=[
                    "block",
                    "chain",
                    "transaction",
                    "ledger",
                    "decentrali",
                ],
            ),
        ],
    ),
    MultiTurnTest(
        name="Scenario 4: Multilingual conversation — Mandarin",
        turns=[
            Turn(
                user_message="你好，请问澳大利亚的首都是哪里？",
                expected_keywords=["堪培拉", "canberra"],
            ),
            Turn(
                user_message="谢谢！悉尼为什么不是首都？",
                expected_keywords=[
                    "墨尔本",
                    "melbourne",
                    "悉尼",
                    "sydney",
                    "折中",
                    "compromise",
                    "首都",
                ],
            ),
        ],
    ),
    MultiTurnTest(
        name="Scenario 5: Correction handling",
        turns=[
            Turn(
                user_message="Who wrote Romeo and Juliet?",
                expected_keywords=["shakespeare"],
            ),
            Turn(
                user_message=(
                    "Actually I meant the movie, not the play. "
                    "Who directed the 1996 film version?"
                ),
                expected_keywords=["luhrmann", "baz"],
            ),
        ],
    ),
]


# ── Helpers ─────────────────────────────────────────────────────────────────


def extract_text_from_events(events: list[dict]) -> str:
    """Extract all text parts from a list of Agent Engine stream events."""
    texts = []
    for event in events:
        if not isinstance(event, dict):
            texts.append(str(event))
            continue
        content = event.get("content", {})
        if not isinstance(content, dict):
            continue
        parts = content.get("parts", [])
        for part in parts:
            if isinstance(part, dict) and "text" in part:
                texts.append(part["text"])
    return "\n".join(texts)


def check_keywords(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(kw.lower() in lower for kw in keywords)


def check_negative_keywords(text: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    lower = text.lower()
    return not any(kw.lower() in lower for kw in keywords)


def print_result(
    name: str, passed: bool, response_text: str, verbose: bool, turn: int | None = None
):
    turn_label = f" [Turn {turn}]" if turn is not None else ""
    status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    print(f"  {status}  {name}{turn_label}")
    if verbose or not passed:
        preview = response_text[:500] + ("..." if len(response_text) > 500 else "")
        indent = "         "
        for line in preview.split("\n"):
            print(f"{indent}{CYAN}{line}{RESET}")
        print()


# ── Query helper ────────────────────────────────────────────────────────────


async def query_agent(adk_app, message: str, user_id: str, session_id: str) -> str:
    events = []
    async for event in adk_app.async_stream_query(
        user_id=user_id,
        session_id=session_id,
        message=message,
    ):
        events.append(event)
    return extract_text_from_events(events)


# ── Test runners ────────────────────────────────────────────────────────────


async def run_single_turn_tests(
    adk_app, verbose: bool
) -> tuple[int, int, list[ConversationLog]]:
    """Run all single-turn tests. Returns (passed, total, conversation_logs)."""
    print(f"\n{BOLD}━━━ Single-Turn Tests ━━━{RESET}\n")
    passed = 0
    total = len(SINGLE_TURN_TESTS)
    logs: list[ConversationLog] = []

    for test in SINGLE_TURN_TESTS:
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        try:
            session = await adk_app.async_create_session(user_id=user_id)
            session_id = session["id"] if isinstance(session, dict) else session.id

            text = await query_agent(adk_app, test.user_message, user_id, session_id)
            kw_pass = check_keywords(text, test.expected_keywords)
            neg_pass = check_negative_keywords(text, test.negative_keywords)
            ok = kw_pass and neg_pass
            if ok:
                passed += 1
            print_result(test.name, ok, text, verbose)

            logs.append(
                ConversationLog(
                    name=test.name,
                    test_type="single_turn",
                    turns=[
                        {"role": "user", "content": test.user_message},
                        {"role": "agent", "content": text},
                    ],
                    keyword_checks=[
                        {
                            "turn": 1,
                            "expected_keywords": test.expected_keywords,
                            "negative_keywords": test.negative_keywords,
                            "passed": ok,
                        }
                    ],
                )
            )
        except Exception as e:  # noqa: BLE001 — test harness records any failure
            print_result(test.name, False, f"ERROR: {e}", verbose)
            logs.append(
                ConversationLog(
                    name=test.name,
                    test_type="single_turn",
                    turns=[
                        {"role": "user", "content": test.user_message},
                        {"role": "agent", "content": f"ERROR: {e}"},
                    ],
                    keyword_checks=[
                        {
                            "turn": 1,
                            "expected_keywords": test.expected_keywords,
                            "negative_keywords": test.negative_keywords,
                            "passed": False,
                            "error": str(e),
                        }
                    ],
                )
            )

    return passed, total, logs


async def run_multi_turn_tests(
    adk_app, verbose: bool
) -> tuple[int, int, list[ConversationLog]]:
    """Run all multi-turn test scenarios. Returns (passed, total, conversation_logs)."""
    print(f"\n{BOLD}━━━ Multi-Turn Tests ━━━{RESET}\n")
    passed = 0
    total = 0
    logs: list[ConversationLog] = []

    for scenario in MULTI_TURN_TESTS:
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        print(f"\n  {YELLOW}{scenario.name}{RESET}")
        conv_turns: list[dict] = []
        kw_checks: list[dict] = []

        try:
            session = await adk_app.async_create_session(user_id=user_id)
            session_id = session["id"] if isinstance(session, dict) else session.id
        except Exception as e:  # noqa: BLE001 — test harness records session-create failure
            for i, turn in enumerate(scenario.turns, start=1):
                total += 1
                kw_checks.append(
                    {
                        "turn": i,
                        "expected_keywords": turn.expected_keywords,
                        "negative_keywords": turn.negative_keywords,
                        "passed": False,
                        "error": f"Session creation failed: {e}",
                    }
                )
                print_result(
                    scenario.name,
                    False,
                    f"ERROR creating session: {e}",
                    verbose,
                    turn=i,
                )
            logs.append(
                ConversationLog(
                    name=scenario.name,
                    test_type="multi_turn",
                    turns=[],
                    keyword_checks=kw_checks,
                )
            )
            continue

        for i, turn in enumerate(scenario.turns, start=1):
            total += 1
            try:
                text = await query_agent(
                    adk_app, turn.user_message, user_id, session_id
                )
                kw_pass = check_keywords(text, turn.expected_keywords)
                neg_pass = check_negative_keywords(text, turn.negative_keywords)
                ok = kw_pass and neg_pass
                if ok:
                    passed += 1
                print_result(scenario.name, ok, text, verbose, turn=i)

                conv_turns.append({"role": "user", "content": turn.user_message})
                conv_turns.append({"role": "agent", "content": text})
                kw_checks.append(
                    {
                        "turn": i,
                        "expected_keywords": turn.expected_keywords,
                        "negative_keywords": turn.negative_keywords,
                        "passed": ok,
                    }
                )
            except Exception as e:  # noqa: BLE001 — test harness records any turn failure
                print_result(scenario.name, False, f"ERROR: {e}", verbose, turn=i)
                conv_turns.append({"role": "user", "content": turn.user_message})
                conv_turns.append({"role": "agent", "content": f"ERROR: {e}"})
                kw_checks.append(
                    {
                        "turn": i,
                        "expected_keywords": turn.expected_keywords,
                        "negative_keywords": turn.negative_keywords,
                        "passed": False,
                        "error": str(e),
                    }
                )

            await asyncio.sleep(1)

        logs.append(
            ConversationLog(
                name=scenario.name,
                test_type="multi_turn",
                turns=conv_turns,
                keyword_checks=kw_checks,
            )
        )

    return passed, total, logs


# ── LLM-as-Judge ────────────────────────────────────────────────────────────


def _build_judge_prompt(rubric_text: str, conversation: ConversationLog) -> str:
    """Build the full judge prompt for a single conversation."""
    conv_lines = []
    for turn in conversation.turns:
        role = "User" if turn["role"] == "user" else "Assistant (Agent)"
        conv_lines.append(f"**{role}:** {turn['content']}")
    conv_text = "\n\n".join(conv_lines)

    return f"""You are evaluating a general-purpose AI assistant. You are judging from
the perspective of a user who asked a question and wants a clear,
accurate, and helpful answer.

Score every applicable dimension from the rubric on a 1-4 scale.
Return a JSON object with these exact keys:
- "scores": object with keys: accuracy, helpfulness, source_usage, clarity, conciseness, tone, multi_part_handling, multilingual_support. Each value is an integer 1-4, or null if N/A for this conversation.
- "justifications": object with the same keys. Each value is a one-sentence justification string, or null if N/A.
- "overall_score": a float rounded to the nearest 0.5 (e.g. 3.0, 3.5, 4.0).

Accuracy rule: if the agent fabricates a source, URL, statistic, or key
fact, the overall_score MUST be 1.0.

<rubric>
{rubric_text}
</rubric>

<conversation>
Test scenario: {conversation.name}

{conv_text}
</conversation>"""


def _parse_judge_response(response_text: str) -> dict | None:
    """Parse the judge response JSON, handling markdown code fences."""
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


async def run_llm_judge(
    conversation_logs: list[ConversationLog],
    project: str,
    location: str,
    verbose: bool,
) -> tuple[float, list[dict]]:
    """Run Gemini 2.5 Pro as judge. Returns (avg_score, list of judge results)."""
    from google import genai

    print(f"\n{BOLD}━━━ LLM Judge Evaluation (Gemini 2.5 Pro) ━━━{RESET}\n")

    rubric_text = RUBRIC_PATH.read_text()
    judge_client = genai.Client(vertexai=True, project=project, location=location)

    all_scores: list[float] = []
    judge_results: list[dict] = []

    for conv in conversation_logs:
        judge_entry: dict = {
            "scenario": conv.name,
            "judge_model": JUDGE_MODEL,
        }

        if not conv.turns:
            print(f"  {DIM}Skipping {conv.name} (no turns recorded){RESET}")
            judge_entry["status"] = "skipped"
            judge_entry["reason"] = "no turns recorded"
            judge_results.append(judge_entry)
            continue

        print(f"  {YELLOW}{conv.name}{RESET}")
        prompt = _build_judge_prompt(rubric_text, conv)

        try:
            response = judge_client.models.generate_content(
                model=JUDGE_MODEL,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )

            result = _parse_judge_response(response.text)

            if result is None:
                print(f"    {RED}Failed to parse judge response{RESET}")
                if verbose:
                    print(f"    {DIM}{response.text[:300]}{RESET}")
                judge_entry["status"] = "parse_error"
                judge_entry["raw_response"] = response.text
                judge_results.append(judge_entry)
                continue

            scores = result.get("scores", {})
            justifications = result.get("justifications", {})
            overall = result.get("overall_score", 0.0)

            for dim_key, dim_label in DIMENSION_LABELS.items():
                score = scores.get(dim_key)
                justification = justifications.get(dim_key)
                if score is None:
                    print(f"    {dim_label:<20s} {DIM}N/A{RESET}")
                else:
                    colour = GREEN if score >= 3 else (YELLOW if score == 2 else RED)
                    just_text = f"  — {justification}" if justification else ""
                    print(f"    {dim_label:<20s} {colour}{score}{RESET}{just_text}")

            overall_colour = (
                GREEN if overall >= 3.0 else (YELLOW if overall >= 2.0 else RED)
            )
            print(f"    {'Overall':<20s} {BOLD}{overall_colour}{overall}{RESET}")
            print()

            all_scores.append(overall)
            judge_entry["status"] = "success"
            judge_entry["scores"] = scores
            judge_entry["justifications"] = justifications
            judge_entry["overall_score"] = overall
            judge_results.append(judge_entry)

        except Exception as e:  # noqa: BLE001 — best-effort judge scoring
            print(f"    {RED}Judge error: {e}{RESET}")
            if verbose:
                import traceback

                traceback.print_exc()
            print()
            judge_entry["status"] = "error"
            judge_entry["error"] = str(e)
            judge_results.append(judge_entry)

    # Summary
    avg = 0.0
    if all_scores:
        avg = sum(all_scores) / len(all_scores)
        avg_colour = GREEN if avg >= 3.0 else (YELLOW if avg >= 2.0 else RED)
        print(f"{BOLD}━━━ Judge Summary ━━━{RESET}")
        print(f"  Conversations evaluated: {len(all_scores)}")
        print(f"  Average overall score:   {avg_colour}{avg:.1f} / 4.0{RESET}")
        print()

    return avg, judge_results


# ── JSON output ─────────────────────────────────────────────────────────────


def save_evaluation_report(
    run_timestamp: str,
    config: dict,
    conversation_logs: list[ConversationLog],
    keyword_summary: dict,
    judge_results: list[dict] | None,
    judge_avg: float | None,
) -> Path:
    """Save the full evaluation report as JSON to evaluation_output/."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Build test cases with full input/output and keyword + judge results
    test_cases = []
    judge_by_scenario = {}
    if judge_results:
        judge_by_scenario = {r["scenario"]: r for r in judge_results}

    for conv in conversation_logs:
        case = {
            "scenario": conv.name,
            "test_type": conv.test_type,
            "conversation": conv.turns,
            "keyword_checks": conv.keyword_checks,
            "keyword_all_passed": all(c["passed"] for c in conv.keyword_checks),
        }
        judge = judge_by_scenario.get(conv.name)
        if judge:
            case["llm_judge"] = judge
        test_cases.append(case)

    report = {
        "run_id": run_timestamp,
        "timestamp_utc": run_timestamp,
        "config": config,
        "summary": {
            "keyword_checks": keyword_summary,
        },
        "test_cases": test_cases,
    }

    if judge_results is not None:
        successful_judges = [r for r in judge_results if r.get("status") == "success"]
        report["summary"]["llm_judge"] = {
            "model": JUDGE_MODEL,
            "conversations_evaluated": len(successful_judges),
            "average_overall_score": round(judge_avg, 2) if judge_avg else 0.0,
            "dimension_averages": _compute_dimension_averages(successful_judges),
        }

    filename = f"{run_timestamp}.json"
    output_path = OUTPUT_DIR / filename
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return output_path


def _compute_dimension_averages(judge_results: list[dict]) -> dict:
    """Compute average score per dimension across all successful judge results."""
    dim_sums: dict[str, list[float]] = {k: [] for k in DIMENSION_LABELS}
    for r in judge_results:
        scores = r.get("scores", {})
        for dim_key in DIMENSION_LABELS:
            val = scores.get(dim_key)
            if val is not None:
                dim_sums[dim_key].append(float(val))

    return {
        dim_key: round(sum(vals) / len(vals), 2) if vals else None
        for dim_key, vals in dim_sums.items()
    }


# ── Main ────────────────────────────────────────────────────────────────────


async def async_main(args):
    run_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    run_single = not args.multi or args.single
    run_multi = not args.single or args.multi

    project = os.environ.get("GOOGLE_CLOUD_PROJECT", DEFAULT_PROJECT)
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", DEFAULT_LOCATION)
    agent_engine_id = os.environ.get("AGENT_ENGINE_ID", DEFAULT_AGENT_ENGINE_ID)

    config = {
        "project": project,
        "location": location,
        "agent_engine_id": agent_engine_id,
        "judge_enabled": args.judge,
        "judge_model": JUDGE_MODEL if args.judge else None,
        "test_scope": "single" if args.single else ("multi" if args.multi else "all"),
    }

    print(f"{BOLD}User Assistant — Deployed Agent Tests{RESET}")
    print(f"  Project:  {project}")
    print(f"  Region:   {location}")
    print(f"  Agent:    {agent_engine_id}")
    if args.judge:
        print(f"  Judge:    {JUDGE_MODEL}")

    # Connect using the vertexai Client API
    print("\nConnecting to Agent Engine...")
    client = vertexai.Client(project=project, location=location)
    adk_app = client.agent_engines.get(name=agent_engine_id)
    print(f"{GREEN}Connected.{RESET}")

    total_passed = 0
    total_tests = 0
    all_logs: list[ConversationLog] = []

    if run_single:
        p, t, logs = await run_single_turn_tests(adk_app, args.verbose)
        total_passed += p
        total_tests += t
        all_logs.extend(logs)

    if run_multi:
        p, t, logs = await run_multi_turn_tests(adk_app, args.verbose)
        total_passed += p
        total_tests += t
        all_logs.extend(logs)

    # ── Keyword Summary ──────────────────────────────────────────────────
    print(f"\n{BOLD}━━━ Keyword Check Summary ━━━{RESET}")
    colour = GREEN if total_passed == total_tests else RED
    print(f"  {colour}{total_passed}/{total_tests} checks passed{RESET}\n")

    keyword_summary = {
        "total_checks": total_tests,
        "passed": total_passed,
        "failed": total_tests - total_passed,
    }

    # ── LLM Judge ────────────────────────────────────────────────────────
    judge_results = None
    judge_avg = None
    if args.judge:
        judge_avg, judge_results = await run_llm_judge(
            all_logs, project, location, args.verbose
        )

    # ── Save JSON report ─────────────────────────────────────────────────
    output_path = save_evaluation_report(
        run_timestamp=run_timestamp,
        config=config,
        conversation_logs=all_logs,
        keyword_summary=keyword_summary,
        judge_results=judge_results,
        judge_avg=judge_avg,
    )
    print(f"{BOLD}Report saved:{RESET} {output_path}")

    return 0 if total_passed == total_tests else 1


def main():
    parser = argparse.ArgumentParser(
        description="Test the deployed User Assistant Agent on Agent Engine"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show full agent responses"
    )
    parser.add_argument(
        "--single", action="store_true", help="Run only single-turn tests"
    )
    parser.add_argument(
        "--multi", action="store_true", help="Run only multi-turn tests"
    )
    parser.add_argument(
        "--judge",
        "-j",
        action="store_true",
        help="Run LLM-as-judge evaluation using Gemini 2.5 Pro after keyword tests",
    )
    args = parser.parse_args()

    exit_code = asyncio.run(async_main(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
