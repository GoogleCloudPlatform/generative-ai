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

"""Comparative test suite: Augmented Assistant vs Baseline.

A simulated user agent drives BOTH conversations with the same opening
message. The user agent decides when the goal is reached or gives up.
Both agents get the same input — the only difference is whether a
personalized swarm fires. An LLM judge then compares the full logs.

Two modes:
1. Sample from profiles.json (default) — same pool as harvest
2. Dedicated eval file (--eval-file) — held-out scenarios with
   explicit goal definitions, expected triggers, and false-positive tests

Usage:
    python test_augmented_agent.py                    # 2 per user, no judge
    python test_augmented_agent.py --judge            # + LLM judge scoring
    python test_augmented_agent.py --verbose          # show full conversations
    python test_augmented_agent.py -n 5               # 5 scenarios per user
    python test_augmented_agent.py --user user_1      # one user only
    python test_augmented_agent.py --baseline-only    # run only baseline
    python test_augmented_agent.py --augmented-only   # run only augmented
    python test_augmented_agent.py --seed 42          # reproducible sampling

    # Final evaluation with dedicated scenarios:
    python test_augmented_agent.py --eval-file evaluation_scenarios_user1.json --judge --verbose
"""

import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from google import genai
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

sys.path.insert(0, str(Path(__file__).parent))

import config as cfg
from harvest.orchestrator import _BASELINE_INSTRUCTION

baseline_agent = Agent(
    name="user_assistant",
    model=cfg.AGENT_MODEL,
    description="Baseline assistant.",
    instruction=_BASELINE_INSTRUCTION,
    tools=[],
)

from augmented_assistant_agent.agent import root_agent as augmented_agent
from augmented_assistant_agent.tools.active_mem import invocation_log
from augmented_assistant_agent.tools.swarm_loader import (
    clear_cache as clear_swarm_cache,
)
from augmented_assistant_agent.tools.swarm_loader import (
    load_swarm,
)
from eval.harness import (
    JUDGE_FALLBACK_MODELS,
    JUDGE_MODEL,
    judge_conversation,
    run_eval_user_turn,
)
from eval.harness import (
    build_style_hints as _build_style_hints,
)

PROFILES_PATH = Path(__file__).parent / "user_profiles" / "profiles.json"
EVAL_SCENARIOS_PATH = Path(__file__).parent / "evaluation_scenarios_user1.json"
RUBRIC_PATH = Path(__file__).parent / "evaluation_rubric_augmented.md"
OUTPUT_DIR = Path(__file__).parent / "evaluation_output"
MAX_TURNS = 6
JUDGE_RETRY_THRESHOLD = 1.0  # Re-judge when |quality_delta| < this value

# ANSI colours
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

_SEMANTIC_MATCH_PROMPT = """\
A user sent this message with the intent "{intent}":
"{user_message}"

Goal: {goal_definition}

The system activated an agent named "{fired_agent}" with this description:
"{agent_description}"

Is this agent a semantically appropriate match for the user's intent and goal?
The agent name may differ from what was expected — focus on whether the agent's
PURPOSE matches what the user needs, not the exact name.

Answer ONLY "YES" or "NO"."""


def _normalize_agent_name(name: str) -> str:
    """Normalize agent name by stripping common suffixes for comparison."""
    s = name.lower().replace("_", " ").strip()
    for suffix in ("ing", "tion", "ation", "ment", "ize", "ise", "es", "s"):
        if s.endswith(suffix) and len(s) > len(suffix) + 2:
            s = s[: -len(suffix)]
            break
    return s


def _fuzzy_agent_name_match(expected: str | None, actual: str | None) -> bool:
    """Check if agent names match allowing for naming variations.

    Handles Jaccard word overlap (>= 0.5) and suffix normalization
    (e.g. 'outlining' vs 'outlines').
    """
    if not expected or not actual:
        return False
    if expected == actual:
        return True
    # Suffix-normalized comparison
    if _normalize_agent_name(expected) == _normalize_agent_name(actual):
        return True
    # Jaccard word overlap
    e_parts = set(expected.lower().replace("_", " ").split())
    a_parts = set(actual.lower().replace("_", " ").split())
    if not e_parts or not a_parts:
        return False
    overlap = len(e_parts & a_parts) / len(e_parts | a_parts)
    return overlap >= 0.5


async def _check_semantic_match(
    intent: str,
    goal_definition: str,
    user_message: str,
    fired_agent: str,
    agent_description: str,
    client,
) -> bool:
    """Check if a fired agent semantically matches the expected intent."""
    prompt = _SEMANTIC_MATCH_PROMPT.format(
        intent=intent,
        user_message=user_message[:500],
        goal_definition=goal_definition,
        fired_agent=fired_agent,
        agent_description=agent_description,
    )
    response = await client.aio.models.generate_content(
        model=cfg.AGENT_MODEL, contents=prompt
    )
    return "yes" in response.text.strip().lower()


DIMENSION_LABELS = {
    "accuracy": "Accuracy",
    "helpfulness": "Helpfulness",
    "personalization": "Personal",
}


# ── Scenario sampling from profiles.json ───────────────────────────────────


def sample_scenarios(
    profiles_path: Path,
    n_per_user: int,
    user_filter: str | None,
    seed: int | None,
) -> list[dict]:
    """Sample n scenarios per user from profiles.json.

    Samples one scenario per intent (round-robin) to maximise diversity.
    Returns list of dicts with keys: user_id, persona, scenario, name.
    """
    profiles = json.loads(profiles_path.read_text())
    rng = random.Random(seed)

    users = profiles["users"]
    if user_filter:
        users = [u for u in users if u["user_id"] == user_filter]
        if not users:
            print(f"{RED}User '{user_filter}' not found in profiles.json{RESET}")
            sys.exit(1)

    sampled = []
    for user in users:
        # Group scenarios by intent
        by_intent: dict[str, list] = {}
        for s in user["scenarios"]:
            by_intent.setdefault(s["intent"], []).append(s)

        # Shuffle intents and pick round-robin
        intents = list(by_intent.keys())
        rng.shuffle(intents)

        picked = []
        intent_idx = 0
        while len(picked) < n_per_user and intent_idx < len(intents) * 5:
            intent = intents[intent_idx % len(intents)]
            available = [s for s in by_intent[intent] if s not in picked]
            if available:
                picked.append(rng.choice(available))
            intent_idx += 1

        for scenario in picked:
            sampled.append(
                {
                    "user_id": user["user_id"],
                    "user_name": user["name"],
                    "persona": user["persona"],
                    "scenario": scenario,
                    "name": f"{user['user_id']}: {scenario['intent']} ({scenario['scenario_id']})",
                }
            )

    return sampled


def load_eval_scenarios(eval_path: Path) -> list[dict]:
    """Load dedicated evaluation scenarios from a JSON file.

    These are held-out scenarios NOT used during harvest, with explicit
    goal definitions and expected trigger info for validation.
    """
    data = json.loads(eval_path.read_text())
    meta = data["metadata"]
    user_id = meta["user_id"]
    persona = meta["persona"]

    scenarios = []
    for s in data["scenarios"]:
        scenarios.append(
            {
                "user_id": user_id,
                "user_name": user_id,
                "persona": persona,
                "scenario": s,
                "name": f"{user_id}: {s['intent']} ({s['scenario_id']})",
                # Eval-specific fields
                "category": s.get("category", "similar"),
                "should_trigger_swarm": s.get("should_trigger_swarm", False),
                "expected_swarm_agent": s.get("expected_swarm_agent"),
                "goal_definition": s.get("goal_definition", ""),
            }
        )
    return scenarios


# ── Simulated user agent for evaluation ───────────────────────────────────
# (Shared functions imported from eval.harness)


# ── Agent conversation runner ─────────────────────────────────────────────


def _extract_text(event) -> str:
    if not (hasattr(event, "content") and event.content):
        return ""
    # Only extract text from final responses, not intermediate tool calls
    # or sub-agent events. This prevents internal reasoning leakage.
    if hasattr(event, "is_final_response") and not event.is_final_response():
        return ""
    parts = event.content.parts if hasattr(event.content, "parts") else []
    return "".join(
        p.text
        for p in parts
        if hasattr(p, "text") and p.text and not getattr(p, "thought", False)
    )


async def run_conversation(
    runner: InMemoryRunner,
    user_id: str,
    persona: str,
    scenario: dict,
    user_client: genai.Client,
    verbose: bool,
    goal_definition: str = "",
    style_hints: str = "",
) -> dict:
    """Run a full conversation driven by the simulated user agent.

    Returns:
        {"turns": [...], "turn_count": int, "goal_reached": bool}
    """
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id
    )

    turns = []
    user_message = scenario["opening_message"]
    goal_reached = False
    max_turns = min(scenario.get("max_turns", MAX_TURNS), MAX_TURNS)

    for turn_num in range(1, max_turns + 1):
        response_parts = []
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part(text=user_message)],
                ),
            ):
                text = _extract_text(event)
                if text:
                    response_parts.append(text)
        except Exception as e:  # noqa: BLE001 — test harness records any turn failure
            print(f"      {RED}[Turn {turn_num}] ERROR: {e}{RESET}")
            response_parts.append(f"(error: {e})")

        assistant_response = (
            "\n".join(response_parts) if response_parts else "(no response)"
        )

        turns.append({"role": "user", "content": user_message})
        turns.append({"role": "assistant", "content": assistant_response})

        if verbose:
            u_preview = user_message[:120] + ("..." if len(user_message) > 120 else "")
            a_preview = assistant_response[:120] + (
                "..." if len(assistant_response) > 120 else ""
            )
            print(f"      [Turn {turn_num}] {CYAN}User:{RESET} {u_preview}")
            print(f"      [Turn {turn_num}] {DIM}Asst:{RESET} {a_preview}")

        # Ask simulated user agent if goal is reached
        if turn_num < max_turns:
            next_message = await run_eval_user_turn(
                user_client,
                persona,
                scenario["intent"],
                scenario["follow_up_strategy"],
                assistant_response,
                turn_num + 1,
                goal_definition=goal_definition,
                style_hints=style_hints,
            )
            if next_message is None:
                goal_reached = True
                if verbose:
                    print(
                        f"      {GREEN}[GOAL REACHED after {turn_num} turn(s)]{RESET}"
                    )
                break
            user_message = next_message
        elif verbose:
            print(f"      {YELLOW}[MAX TURNS reached ({max_turns})]{RESET}")

    return {
        "turns": turns,
        "turn_count": len(turns) // 2,
        "goal_reached": goal_reached,
    }


# ── LLM Judge ──────────────────────────────────────────────────────────────
# (Shared functions imported from eval.harness)


# ── Main ────────────────────────────────────────────────────────────────────


async def async_main(args):
    run_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    run_baseline = not args.augmented_only
    run_augmented = not args.baseline_only

    # Load scenarios
    using_eval_file = args.eval_file is not None
    if using_eval_file:
        eval_path = Path(args.eval_file)
        if not eval_path.is_absolute():
            eval_path = Path(__file__).parent / eval_path
        scenarios = load_eval_scenarios(eval_path)
        source_label = f"eval file: {eval_path.name}"
    else:
        scenarios = sample_scenarios(PROFILES_PATH, args.n, args.user, args.seed)
        source_label = f"profiles.json ({args.n} per user)"

    if not scenarios:
        print(f"{RED}No scenarios to run.{RESET}")
        sys.exit(1)

    print(f"{BOLD}Augmented vs Baseline — User-Agent-Driven Evaluation{RESET}")
    print(f"  Source:    {source_label}")
    print(f"  Scenarios: {len(scenarios)}")
    if using_eval_file:
        similar = sum(1 for s in scenarios if s.get("category") == "similar")
        different = sum(1 for s in scenarios if s.get("category") == "different")
        print(f"  Similar (should trigger):  {similar}")
        print(f"  Different (false-positive test): {different}")
    print(f"  Max turns: {MAX_TURNS}")
    if not using_eval_file:
        print(f"  Seed:      {args.seed}")
    print(f"  Baseline:  {'yes' if run_baseline else 'skip'}")
    print(f"  Augmented: {'yes' if run_augmented else 'skip'}")
    if args.judge:
        print(
            f"  Judge:     {JUDGE_MODEL} (fallback: {', '.join(JUDGE_FALLBACK_MODELS)})"
        )

    # Clear swarm cache to pick up any trigger changes
    clear_swarm_cache()

    baseline_runner = InMemoryRunner(agent=baseline_agent)
    augmented_runner = InMemoryRunner(agent=augmented_agent)
    user_client = cfg.new_client()

    results = []
    judge_client = cfg.new_client() if args.judge else None
    rubric_text = RUBRIC_PATH.read_text() if args.judge else ""

    for i, scenario_info in enumerate(scenarios, 1):
        user_id = scenario_info["user_id"]
        scenario = scenario_info["scenario"]
        goal_definition = scenario_info.get("goal_definition", "") or scenario.get(
            "goal_definition", ""
        )
        category = scenario_info.get("category", "")
        should_trigger = scenario_info.get("should_trigger_swarm")
        expected_agent = scenario_info.get("expected_swarm_agent")

        # Check swarm availability
        swarm_dir = Path(__file__).parent / "swarms" / user_id
        has_swarm = swarm_dir.exists() and (swarm_dir / "triggers.json").exists()
        swarm_label = f"{GREEN}swarm{RESET}" if has_swarm else f"{DIM}no swarm{RESET}"

        # Category label for eval-file mode
        if category:
            cat_color = GREEN if category == "similar" else CYAN
            cat_label = f" [{cat_color}{category}{RESET}]"
        else:
            cat_label = ""

        print(
            f"\n{YELLOW}[{i}/{len(scenarios)}] {scenario_info['name']}{RESET}{cat_label}"
        )
        print(
            f"  [{swarm_label}] strategy={scenario['follow_up_strategy']}, "
            f"max_turns={min(scenario.get('max_turns', MAX_TURNS), MAX_TURNS)}"
        )
        if goal_definition:
            print(
                f"  {DIM}goal: {goal_definition[:100]}{'...' if len(goal_definition) > 100 else ''}{RESET}"
            )
        print(
            f"  {DIM}msg: {scenario['opening_message'][:100]}{'...' if len(scenario['opening_message']) > 100 else ''}{RESET}"
        )

        result = {
            "name": scenario_info["name"],
            "user_id": user_id,
            "intent": scenario["intent"],
            "scenario_id": scenario["scenario_id"],
            "has_swarm": has_swarm,
            "follow_up_strategy": scenario["follow_up_strategy"],
            "opening_message": scenario["opening_message"],
        }
        if category:
            result["category"] = category
        if should_trigger is not None:
            result["should_trigger_swarm"] = should_trigger
            result["expected_swarm_agent"] = expected_agent
        if goal_definition:
            result["goal_definition"] = goal_definition

        # Load user style hints for simulated user
        _style_hints = ""
        style_path = Path(__file__).parent / "swarms" / user_id / "user_style.json"
        if style_path.exists():
            try:
                _user_style = json.loads(style_path.read_text())
                _style_hints = _build_style_hints(_user_style)
            except (json.JSONDecodeError, OSError):
                pass

        # Run baseline
        baseline_result = None
        if run_baseline:
            print(f"  {DIM}Running baseline...{RESET}")
            baseline_result = await run_conversation(
                baseline_runner,
                user_id,
                scenario_info["persona"],
                scenario,
                user_client,
                args.verbose,
                goal_definition=goal_definition,
                style_hints=_style_hints,
            )
            gr = (
                f"{GREEN}yes{RESET}"
                if baseline_result["goal_reached"]
                else f"{YELLOW}no{RESET}"
            )
            print(
                f"    Baseline: {baseline_result['turn_count']} turns, goal reached: {gr}"
            )
            result["baseline"] = baseline_result

        # Run augmented
        augmented_result = None
        if run_augmented:
            invocation_log.clear()  # Reset before each augmented run
            print(f"  {DIM}Running augmented...{RESET}")
            augmented_result = await run_conversation(
                augmented_runner,
                user_id,
                scenario_info["persona"],
                scenario,
                user_client,
                args.verbose,
                goal_definition=goal_definition,
                style_hints=_style_hints,
            )
            gr = (
                f"{GREEN}yes{RESET}"
                if augmented_result["goal_reached"]
                else f"{YELLOW}no{RESET}"
            )
            print(
                f"    Augmented: {augmented_result['turn_count']} turns, goal reached: {gr}"
            )
            result["augmented"] = augmented_result

            # Check swarm trigger correctness (eval-file mode)
            if should_trigger is not None and augmented_result:
                # Read the actual invocation log from active_mem
                # Look for log entries added during this conversation
                swarm_fired = False
                fired_agent = None
                if invocation_log:
                    # Check the most recent entries for this conversation
                    for entry in reversed(invocation_log):
                        if entry["action"] in ("auto", "suggest"):
                            swarm_fired = True
                            fired_agent = entry["agent_name"]
                            break
                        if entry["action"] == "none":
                            break

                result["swarm_fired"] = swarm_fired
                if fired_agent:
                    result["fired_agent"] = fired_agent

                if should_trigger and swarm_fired:
                    # Exact name match is a fast shortcut
                    if fired_agent == expected_agent:
                        agent_match = True
                    else:
                        # Always use semantic LLM check when names differ
                        # (agent names are unstable across regeneration runs)
                        swarm = load_swarm(user_id)
                        agent_desc = (
                            swarm["triggers"]
                            .get(fired_agent, {})
                            .get("description", "")
                        )
                        agent_match = await _check_semantic_match(
                            intent=scenario_info.get("intent", ""),
                            goal_definition=goal_definition or "",
                            user_message=scenario["opening_message"][:500],
                            fired_agent=fired_agent,
                            agent_description=agent_desc,
                            client=user_client,
                        )
                    if agent_match:
                        label = (
                            "CORRECT"
                            if fired_agent == expected_agent
                            else "CORRECT (semantic)"
                        )
                        print(f"    {GREEN}Swarm: {label} — {fired_agent} fired{RESET}")
                    else:
                        print(
                            f"    {YELLOW}Swarm: FIRED but wrong agent — "
                            f"got {fired_agent}, expected {expected_agent}{RESET}"
                        )
                    result["trigger_correct"] = agent_match
                elif should_trigger and not swarm_fired:
                    # Check if expected agent even exists in the swarm
                    swarm_data = load_swarm(user_id)
                    agent_exists = expected_agent in swarm_data.get(
                        "agents", {}
                    ) or any(
                        _fuzzy_agent_name_match(expected_agent, a)
                        for a in swarm_data.get("agents", {})
                    )
                    if not agent_exists:
                        print(
                            f"    {YELLOW}Swarm: AGENT MISSING — {expected_agent} not in swarm{RESET}"
                        )
                        result["trigger_correct"] = None  # not a trigger failure
                        result["agent_missing"] = True
                    else:
                        print(
                            f"    {RED}Swarm: MISSED — expected {expected_agent} but nothing fired{RESET}"
                        )
                        result["trigger_correct"] = False
                elif not should_trigger and not swarm_fired:
                    print(
                        f"    {GREEN}Swarm: CORRECT — no trigger expected, none fired{RESET}"
                    )
                    result["trigger_correct"] = True
                elif not should_trigger and swarm_fired:
                    print(
                        f"    {RED}Swarm: FALSE POSITIVE — {fired_agent} fired unexpectedly{RESET}"
                    )
                    result["trigger_correct"] = False

                # Clear log for next test case
                invocation_log.clear()

        # Turn comparison
        if baseline_result and augmented_result:
            b_turns = baseline_result["turn_count"]
            a_turns = augmented_result["turn_count"]
            if b_turns > 0:
                reduction = (b_turns - a_turns) / b_turns * 100
                result["turn_reduction_pct"] = round(reduction, 1)
                if a_turns < b_turns:
                    print(
                        f"  {GREEN}Turn reduction: {reduction:.0f}% ({b_turns} → {a_turns}){RESET}"
                    )
                elif a_turns == b_turns:
                    print(f"  {YELLOW}Same turns: {b_turns} each{RESET}")
                else:
                    print(
                        f"  {RED}More turns: {b_turns} → {a_turns} (+{a_turns - b_turns}){RESET}"
                    )

        # LLM Judge
        if args.judge and (baseline_result or augmented_result):
            judge_result = await judge_conversation(
                scenario_info,
                baseline_result,
                augmented_result,
                rubric_text,
                judge_client,
            )

            # ── Compute burden winner (programmatic) ──────────────
            burden_winner = "tie"
            if baseline_result and augmented_result:
                b_turns = baseline_result["turn_count"]
                a_turns = augmented_result["turn_count"]
                b_goal = baseline_result["goal_reached"]
                a_goal = augmented_result["goal_reached"]
                if a_goal and not b_goal:
                    burden_winner = "augmented"
                elif b_goal and not a_goal:
                    burden_winner = "baseline"
                elif a_turns < b_turns:
                    burden_winner = "augmented"
                elif b_turns < a_turns:
                    burden_winner = "baseline"
                result["burden_winner"] = burden_winner

            # ── Compute quality winner (LLM judge with retry) ─────
            def _get_quality_winner(jr):
                """Extract quality_winner from judge result."""
                if not jr:
                    return "tie"
                return jr.get("quality_winner", "tie")

            def _get_quality_delta(jr):
                """Compute quality delta from scores (avg of 4 dimensions)."""
                if not jr:
                    return 0.0
                bl = jr.get("baseline", {})
                aug = jr.get("augmented", {})
                dims = ["accuracy", "helpfulness", "personalization"]
                bl_vals = [bl.get(d, 0) for d in dims if bl.get(d) is not None]
                aug_vals = [aug.get(d, 0) for d in dims if aug.get(d) is not None]
                bl_avg = sum(bl_vals) / len(bl_vals) if bl_vals else 0
                aug_avg = sum(aug_vals) / len(aug_vals) if aug_vals else 0
                return aug_avg - bl_avg

            if judge_result:
                winner1 = _get_quality_winner(judge_result)
                delta1 = _get_quality_delta(judge_result)

                if abs(delta1) < JUDGE_RETRY_THRESHOLD:
                    # Close call — retry
                    judge_result2 = await judge_conversation(
                        scenario_info,
                        baseline_result,
                        augmented_result,
                        rubric_text,
                        judge_client,
                    )
                    winner2 = _get_quality_winner(judge_result2)

                    if winner2 == winner1:
                        judge_result["judge_runs"] = 2
                        judge_result["consensus"] = "2/2"
                    else:
                        judge_result3 = await judge_conversation(
                            scenario_info,
                            baseline_result,
                            augmented_result,
                            rubric_text,
                            judge_client,
                        )
                        winner3 = _get_quality_winner(judge_result3)

                        votes = [winner1, winner2, winner3]
                        from collections import Counter

                        majority_winner, majority_count = Counter(votes).most_common(1)[
                            0
                        ]

                        if majority_winner == winner2 and judge_result2:
                            judge_result = judge_result2
                        elif majority_winner == winner3 and judge_result3:
                            judge_result = judge_result3

                        judge_result["judge_runs"] = 3
                        judge_result["consensus"] = f"majority {majority_count}/3"
                        judge_result["votes"] = votes

                # Store final quality results
                result["judge"] = judge_result
                result["quality_winner"] = _get_quality_winner(judge_result)
                result["quality_delta"] = round(_get_quality_delta(judge_result), 2)

            # ── Print results ─────────────────────────────────────
            if judge_result:

                def _print_agent_quality(label, agent_data):
                    if not agent_data:
                        return
                    dims = {
                        "accuracy": "Acc",
                        "helpfulness": "Help",
                        "personalization": "Personal",
                    }
                    vals = []
                    parts = []
                    for key, short in dims.items():
                        v = agent_data.get(key)
                        if v is not None:
                            vals.append(v)
                            c = GREEN if v >= 3 else (YELLOW if v == 2 else RED)
                            parts.append(f"{short}={c}{v}{RESET}")
                    avg = sum(vals) / len(vals) if vals else 0
                    oc = GREEN if avg >= 3 else RED
                    print(
                        f"    {DIM}{label}:{RESET}  "
                        + "  ".join(parts)
                        + f"  Avg={BOLD}{oc}{avg:.1f}{RESET}"
                    )

                _print_agent_quality("Baseline", judge_result.get("baseline"))
                _print_agent_quality("Augmented", judge_result.get("augmented"))

                # Burden winner
                bc = (
                    GREEN
                    if burden_winner == "augmented"
                    else (RED if burden_winner == "baseline" else YELLOW)
                )
                print(f"    Burden:  {BOLD}{bc}{burden_winner}{RESET}")

                # Quality winner
                qw = result.get("quality_winner", "tie")
                qd = result.get("quality_delta", 0)
                qc = (
                    GREEN
                    if qw == "augmented"
                    else (RED if qw == "baseline" else YELLOW)
                )
                print(
                    f"    Quality: {BOLD}{qc}{qw}{RESET}"
                    f"  (delta: {'+' if qd > 0 else ''}{qd})"
                )

                runs = judge_result.get("judge_runs", 1)
                if runs > 1:
                    consensus = judge_result.get("consensus", "")
                    votes = judge_result.get("votes")
                    extra = f" votes={votes}" if votes else ""
                    print(f"    {DIM}(judge: {runs} runs, {consensus}{extra}){RESET}")

                summary = judge_result.get("quality_summary", "")
                if summary:
                    words = summary.split()
                    line = "    "
                    for w in words:
                        if len(line) + len(w) > 100:
                            print(line)
                            line = "    " + w
                        else:
                            line += " " + w if line.strip() else "    " + w
                    if line.strip():
                        print(line)

        results.append(result)
        await asyncio.sleep(0.5)

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'━' * 60}{RESET}")
    print(f"{BOLD}  HEAD-TO-HEAD COMPARISON SUMMARY{RESET}")
    print(f"{BOLD}{'━' * 60}{RESET}")

    # Split by category (eval-file) or swarm presence (profiles.json)
    similar_results = [r for r in results if r.get("category") == "similar"]
    different_results = [r for r in results if r.get("category") == "different"]
    swarm_results = [r for r in results if r.get("has_swarm")]
    no_swarm_results = [r for r in results if not r.get("has_swarm")]

    def _print_turn_stats(label, result_set):
        if not result_set:
            return
        b_turns = [r["baseline"]["turn_count"] for r in result_set if "baseline" in r]
        a_turns = [r["augmented"]["turn_count"] for r in result_set if "augmented" in r]
        b_goals = [r["baseline"]["goal_reached"] for r in result_set if "baseline" in r]
        a_goals = [
            r["augmented"]["goal_reached"] for r in result_set if "augmented" in r
        ]

        print(f"\n  {BOLD}{label} ({len(result_set)} tests):{RESET}")
        if b_turns:
            avg_b = sum(b_turns) / len(b_turns)
            print(
                f"    Avg baseline turns:   {avg_b:.1f}  "
                f"(goal reached: {sum(b_goals)}/{len(b_goals)})"
            )
        if a_turns:
            avg_a = sum(a_turns) / len(a_turns)
            print(
                f"    Avg augmented turns:  {avg_a:.1f}  "
                f"(goal reached: {sum(a_goals)}/{len(a_goals)})"
            )
        if b_turns and a_turns:
            avg_b = sum(b_turns) / len(b_turns)
            avg_a = sum(a_turns) / len(a_turns)
            if avg_b > 0:
                reduction = (avg_b - avg_a) / avg_b * 100
                c = GREEN if reduction > 0 else (RED if reduction < 0 else YELLOW)
                print(f"    Avg turn reduction:   {c}{reduction:.1f}%{RESET}")

    # Trigger accuracy (eval-file mode)
    trigger_results = [r for r in results if "trigger_correct" in r]
    if trigger_results:
        # Exclude agent_missing from accuracy count (agent doesn't exist in swarm)
        scorable = [r for r in trigger_results if r["trigger_correct"] is not None]
        missing = sum(1 for r in trigger_results if r.get("agent_missing"))
        correct = sum(1 for r in scorable if r["trigger_correct"])
        total = len(scorable)
        tp = sum(
            1
            for r in scorable
            if r.get("should_trigger_swarm") and r.get("swarm_fired")
        )
        fn = sum(
            1
            for r in scorable
            if r.get("should_trigger_swarm")
            and not r.get("swarm_fired")
            and not r.get("agent_missing")
        )
        tn = sum(
            1
            for r in scorable
            if not r.get("should_trigger_swarm") and not r.get("swarm_fired")
        )
        fp = sum(
            1
            for r in scorable
            if not r.get("should_trigger_swarm") and r.get("swarm_fired")
        )

        acc_color = (
            GREEN if correct == total else (YELLOW if correct >= total * 0.7 else RED)
        )
        print(f"\n  {BOLD}Swarm Trigger Accuracy:{RESET}")
        print(
            f"    Overall: {acc_color}{correct}/{total} correct ({correct / total * 100:.0f}%){RESET}"
        )
        if missing:
            print(
                f"    Agent missing:   {YELLOW}{missing}{RESET}  (expected agent not in swarm — excluded from accuracy)"
            )
        print(f"    True positives:  {GREEN}{tp}{RESET}  (should trigger, did trigger)")
        print(
            f"    False negatives: {RED}{fn}{RESET}  (should trigger, did NOT trigger)"
        )
        print(f"    True negatives:  {GREEN}{tn}{RESET}  (should NOT trigger, did not)")
        print(
            f"    False positives: {RED}{fp}{RESET}  (should NOT trigger, DID trigger)"
        )

    # Category-based splits (eval-file mode)
    if similar_results or different_results:
        _print_turn_stats("Similar (should trigger swarm)", similar_results)
        _print_turn_stats("Different (false-positive test)", different_results)
    else:
        _print_turn_stats("With swarm", swarm_results)
        _print_turn_stats("Without swarm", no_swarm_results)
    _print_turn_stats("Overall", results)

    # Burden stats (programmatic)
    def _print_burden_stats(label, result_set):
        burden_wins = {"baseline": 0, "augmented": 0, "tie": 0}
        for r in result_set:
            bw = r.get("burden_winner", "tie")
            burden_wins[bw] = burden_wins.get(bw, 0) + 1
        if not any(v > 0 for v in burden_wins.values()):
            return
        print(f"\n  {BOLD}{label} — Burden (turns):{RESET}")
        print(
            f"    Win/Loss/Tie: "
            f"{GREEN}Aug {burden_wins['augmented']}{RESET} / "
            f"{RED}Base {burden_wins['baseline']}{RESET} / "
            f"{YELLOW}Tie {burden_wins['tie']}{RESET}"
        )

    if similar_results or different_results:
        _print_burden_stats("Similar (should trigger swarm)", similar_results)
        _print_burden_stats("Different (false-positive test)", different_results)
    else:
        _print_burden_stats("With swarm", swarm_results)
        _print_burden_stats("Without swarm", no_swarm_results)
    _print_burden_stats("Overall", results)

    # Quality stats (LLM judge)
    if args.judge:

        def _print_quality_stats(label, result_set):
            quality_wins = {"baseline": 0, "augmented": 0, "tie": 0}
            bl_avgs = []
            aug_avgs = []
            dims = ["accuracy", "helpfulness", "personalization"]
            for r in result_set:
                qw = r.get("quality_winner", "tie")
                quality_wins[qw] = quality_wins.get(qw, 0) + 1
                judge = r.get("judge", {})
                bl = judge.get("baseline", {})
                aug = judge.get("augmented", {})
                bl_vals = [bl.get(d, 0) for d in dims if bl.get(d) is not None]
                aug_vals = [aug.get(d, 0) for d in dims if aug.get(d) is not None]
                if bl_vals:
                    bl_avgs.append(sum(bl_vals) / len(bl_vals))
                if aug_vals:
                    aug_avgs.append(sum(aug_vals) / len(aug_vals))

            if not (bl_avgs or aug_avgs):
                return

            print(
                f"\n  {BOLD}{label} — Quality (accuracy + helpfulness + personalization):{RESET}"
            )
            if bl_avgs:
                avg_b = sum(bl_avgs) / len(bl_avgs)
                cb = GREEN if avg_b >= 3 else RED
                print(f"    Avg baseline quality:   {cb}{avg_b:.2f} / 4.0{RESET}")
            if aug_avgs:
                avg_a = sum(aug_avgs) / len(aug_avgs)
                ca = GREEN if avg_a >= 3 else RED
                print(f"    Avg augmented quality:  {ca}{avg_a:.2f} / 4.0{RESET}")
            if bl_avgs and aug_avgs:
                delta = sum(aug_avgs) / len(aug_avgs) - sum(bl_avgs) / len(bl_avgs)
                dc = GREEN if delta > 0 else (RED if delta < 0 else YELLOW)
                print(
                    f"    Quality delta (aug-base): {dc}{'+' if delta > 0 else ''}{delta:.2f}{RESET}"
                )
            if any(v > 0 for v in quality_wins.values()):
                print(
                    f"    Win/Loss/Tie: "
                    f"{GREEN}Aug {quality_wins['augmented']}{RESET} / "
                    f"{RED}Base {quality_wins['baseline']}{RESET} / "
                    f"{YELLOW}Tie {quality_wins['tie']}{RESET}"
                )

        if similar_results or different_results:
            _print_quality_stats("Similar (should trigger swarm)", similar_results)
            _print_quality_stats("Different (false-positive test)", different_results)
        else:
            _print_quality_stats("With swarm", swarm_results)
            _print_quality_stats("Without swarm", no_swarm_results)
        _print_quality_stats("Overall", results)

    # Save report
    OUTPUT_DIR.mkdir(exist_ok=True)
    summary_data = {
        "total_tests": len(results),
        "tests_with_swarm": len(swarm_results),
        "tests_without_swarm": len(no_swarm_results),
        "max_turns": MAX_TURNS,
    }
    if using_eval_file:
        summary_data["eval_file"] = str(eval_path.name)
        summary_data["similar_tests"] = len(similar_results)
        summary_data["different_tests"] = len(different_results)
        if trigger_results:
            scorable = [r for r in trigger_results if r["trigger_correct"] is not None]
            missing = sum(1 for r in trigger_results if r.get("agent_missing"))
            correct = sum(1 for r in scorable if r["trigger_correct"])
            summary_data["trigger_accuracy"] = f"{correct}/{len(scorable)}"
            if missing:
                summary_data["agents_missing"] = missing
    else:
        summary_data["n_per_user"] = args.n
        summary_data["seed"] = args.seed

    report = {
        "run_id": run_timestamp,
        "timestamp_utc": run_timestamp,
        "config": {
            "baseline": run_baseline,
            "augmented": run_augmented,
            "judge": args.judge,
            "eval_file": str(eval_path.name) if using_eval_file else None,
            "n_per_user": args.n if not using_eval_file else None,
            "seed": args.seed if not using_eval_file else None,
            "max_turns": MAX_TURNS,
        },
        "summary": summary_data,
        "test_cases": results,
    }
    suffix = "final_eval" if using_eval_file else "comparison"
    output_path = OUTPUT_DIR / f"{run_timestamp}_{suffix}.json"
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n{BOLD}Report saved:{RESET} {output_path}")


async def calibrate_embeddings(user_id: str):
    """Print embedding similarity distributions for threshold tuning.

    Embeds each eval scenario's user message and scores against all
    agents' scope embeddings. Reports positive (expected agent) vs
    negative (other agents) score distributions and recommends a threshold.
    """
    import numpy as np

    client = cfg.new_client()

    # Find eval file for this user
    eval_path = Path(__file__).parent / f"evaluation_scenarios_{user_id}.json"
    if not eval_path.exists():
        print(f"{RED}No eval file found: {eval_path}{RESET}")
        return
    scenarios = load_eval_scenarios(eval_path)
    swarm_data = load_swarm(user_id)
    triggers = swarm_data.get("triggers", {})

    # Check embeddings exist
    has_emb = any(cfg.get("scope_embedding") for cfg in triggers.values())
    if not has_emb:
        print(
            f"{RED}No scope_embedding found in {user_id} triggers. "
            f"Regenerate swarm first.{RESET}"
        )
        return

    positive_scores = []
    negative_scores = []

    for sc in scenarios:
        msg = sc["scenario"]["opening_message"]
        expected = sc.get("expected_swarm_agent")
        category = sc.get("category", "similar")

        embed_resp = await client.aio.models.embed_content(
            model=cfg.EMBED_MODEL,
            contents=msg[:2000],
        )
        msg_emb = np.array(embed_resp.embeddings[0].values, dtype=np.float32)

        for agent_name, config in triggers.items():
            scope_emb = config.get("scope_embedding")
            if not scope_emb:
                continue
            scope_vec = np.array(scope_emb, dtype=np.float32)
            sim = float(
                np.dot(msg_emb, scope_vec)
                / (np.linalg.norm(msg_emb) * np.linalg.norm(scope_vec) + 1e-9)
            )

            is_expected = (
                category == "similar"
                and expected
                and _fuzzy_agent_name_match(expected, agent_name)
            )
            if is_expected:
                positive_scores.append((sim, sc["scenario"]["scenario_id"], agent_name))
            else:
                negative_scores.append((sim, sc["scenario"]["scenario_id"], agent_name))

    print(f"\n{BOLD}Embedding Calibration — {user_id}{RESET}")
    print(f"  Agents: {len(triggers)}  Scenarios: {len(scenarios)}")
    print(
        f"  Positive pairs: {len(positive_scores)}  Negative pairs: {len(negative_scores)}"
    )

    if positive_scores:
        pos_vals = [s[0] for s in positive_scores]
        print(f"\n  {GREEN}Positive scores (expected agent):{RESET}")
        print(
            f"    min={min(pos_vals):.3f}  mean={sum(pos_vals) / len(pos_vals):.3f}  "
            f"max={max(pos_vals):.3f}"
        )
        for sim, sid, agent in sorted(positive_scores, key=lambda x: x[0]):
            print(f"    {sim:.3f}  {sid} → {agent}")

    if negative_scores:
        neg_vals = [s[0] for s in negative_scores]
        top_neg = sorted(negative_scores, key=lambda x: x[0], reverse=True)[:10]
        print(f"\n  {RED}Negative scores (non-matching, top 10):{RESET}")
        print(
            f"    min={min(neg_vals):.3f}  mean={sum(neg_vals) / len(neg_vals):.3f}  "
            f"max={max(neg_vals):.3f}"
        )
        for sim, sid, agent in top_neg:
            print(f"    {sim:.3f}  {sid} → {agent}")

    if positive_scores and negative_scores:
        pos_min = min(s[0] for s in positive_scores)
        neg_max = max(s[0] for s in negative_scores)
        gap = pos_min - neg_max
        rec = (pos_min + neg_max) / 2
        color = GREEN if gap > 0.05 else (YELLOW if gap > 0 else RED)
        print(f"\n  {BOLD}Separation gap:{RESET} {color}{gap:.3f}{RESET}")
        print(f"  {BOLD}Recommended threshold:{RESET} {rec:.3f}")
        if gap <= 0:
            print(
                f"  {RED}WARNING: distributions overlap — "
                f"embedding matching alone may produce errors{RESET}"
            )


def main():
    parser = argparse.ArgumentParser(
        description="Compare augmented assistant vs baseline (user-agent driven)"
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--judge", "-j", action="store_true", help="Run LLM-as-judge evaluation"
    )
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--augmented-only", action="store_true")
    parser.add_argument(
        "-n", type=int, default=2, help="Number of scenarios per user (default: 2)"
    )
    parser.add_argument("--user", type=str, help="Run for a specific user only")
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for scenario sampling (default: 42)",
    )
    parser.add_argument(
        "--eval-file",
        type=str,
        default=None,
        help="Path to dedicated evaluation scenarios JSON "
        "(e.g., evaluation_scenarios_user1.json)",
    )
    parser.add_argument(
        "--calibrate-embeddings",
        action="store_true",
        help="Print embedding similarity distributions for threshold tuning",
    )
    args = parser.parse_args()
    if args.calibrate_embeddings:
        if not args.user:
            print("Error: --calibrate-embeddings requires --user")
            sys.exit(1)
        asyncio.run(calibrate_embeddings(args.user))
    else:
        asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
