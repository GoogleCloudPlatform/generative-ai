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

"""Orchestrator for generating conversational history.

Drives simulated user <-> assistant conversations and saves them to history/.
Uses the baseline user_assistant_agent locally via google.adk.runners.InMemoryRunner.

Usage:
    python harvest/orchestrator.py                        # all users, all scenarios
    python harvest/orchestrator.py --user user_1          # one user
    python harvest/orchestrator.py --user user_1 --limit 5  # test run
    python harvest/orchestrator.py --verbose              # print conversations
    python harvest/orchestrator.py --resume               # skip existing sessions
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load env from the project-root .env
load_dotenv(Path(__file__).parent.parent / ".env")

from google import genai
from google.adk.runners import InMemoryRunner
from google.genai import types

# Add parent to path so we can import baseline agent components
sys.path.insert(0, str(Path(__file__).parent.parent))
# Build a harvest-compatible version of the baseline agent.
# Google Cloud rejects mixing google_search (grounding tool) with function-call
# tools (memory), so we use google_search only — memory isn't needed for
# history generation since each scenario runs in a fresh session.
import config as cfg
from google.adk.agents import Agent
from google.adk.tools import google_search
from harvest.user_agent import UserAgent

_BASELINE_INSTRUCTION = """\
You are a helpful, general-purpose AI assistant.

## Your Role
You help users with any question, task, or topic they bring to you.
You can answer factual questions, explain concepts, help with writing,
brainstorm ideas, do math and reasoning, summarise information, and
much more.

## Your Personality
- Friendly, clear, and efficient
- You adapt your tone to the user -- casual for casual questions,
  more detailed and precise for technical or professional queries
- You never talk down to the user
- You are patient with follow-up questions

## Greeting
When the user starts a conversation, greet them briefly:
"Hi! I'm your AI assistant. How can I help you today?"

## How to Respond

1. UNDERSTAND the user's question or request.
2. If you can answer confidently from your training knowledge, do so
   directly.
3. If the question is ambiguous, ask ONE targeted clarifying question
   before answering. Do not guess when clarity is easy to obtain.
5. Structure your response clearly:
   - Lead with the direct answer or key takeaway
   - Follow with supporting detail or context if helpful
   - Use formatting (bold, lists, headings) when it aids readability

## Rules
- Be honest about uncertainty -- say "I'm not sure" rather than fabricating
- Do not make up URLs, citations, or sources
- If the user's request spans multiple topics, address each one clearly
- In follow-up turns, do not repeat information you already provided
- Respect the user's time -- be thorough but not verbose

## Multilingual Support
- If the user writes in another language, respond in that language
- You can translate between languages when asked
- If referencing English-only resources, mention that to the user

## Sign-off
After answering, ask: "Is there anything else I can help with?"
"""

# The harvest agent adds google_search for richer history generation.
# _BASELINE_INSTRUCTION (above) is the canonical tool-neutral instruction
# imported by test_augmented_agent.py for baseline evaluation.
_HARVEST_INSTRUCTION = (
    _BASELINE_INSTRUCTION.rstrip()
    + """

## Web Search
You also have access to the google_search tool.
- Use it when the question requires current information (news, prices,
  weather, recent events, live data)
- Use it for specific facts you are not confident about
- When providing information from web search, briefly note where it came from
- If web search returns no useful results, say so and offer alternatives
"""
)

root_agent = Agent(
    name="user_assistant",
    model=cfg.HARVEST_ASSISTANT_MODEL,
    description="Baseline assistant for history harvest (with search).",
    instruction=_HARVEST_INSTRUCTION,
    tools=[google_search],
)

PROFILES_PATH = Path(__file__).parent.parent / "user_profiles" / "profiles.json"
HISTORY_DIR = Path(__file__).parent.parent / "history"

# ANSI colours
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _extract_text(event) -> str:
    """Extract text from a single ADK runner event."""
    if hasattr(event, "content") and event.content:
        parts = event.content.parts if hasattr(event.content, "parts") else []
        return "".join(p.text for p in parts if hasattr(p, "text") and p.text)
    return ""


async def run_scenario(
    user_profile: dict,
    scenario: dict,
    runner: InMemoryRunner,
    user_agent_client: genai.Client,
    verbose: bool,
) -> dict:
    """Run a single scenario and return the session log."""
    user_id = user_profile["user_id"]

    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id
    )

    user_agent = UserAgent(
        persona=user_profile["persona"],
        intent=scenario["intent"],
        follow_up_strategy=scenario["follow_up_strategy"],
        client=user_agent_client,
    )

    turns = []
    max_turns = scenario["max_turns"]

    for turn_num in range(1, max_turns + 1):
        # Get user message
        if turn_num == 1:
            user_message = scenario["opening_message"]
        else:
            last_assistant_msg = turns[-1]["content"]
            user_message = await user_agent.generate_follow_up(
                assistant_response=last_assistant_msg,
                turn_number=turn_num,
            )

        # Send to assistant
        response_parts = []
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

        assistant_response = (
            "\n".join(response_parts) if response_parts else "(no response)"
        )

        turns.append({"role": "user", "content": user_message})
        turns.append({"role": "assistant", "content": assistant_response})

        if verbose:
            print(
                f"    [Turn {turn_num}] {CYAN}User:{RESET} {user_message[:120]}{'...' if len(user_message) > 120 else ''}"
            )
            print(
                f"    [Turn {turn_num}] {DIM}Asst:{RESET} {assistant_response[:120]}{'...' if len(assistant_response) > 120 else ''}"
            )

    return {
        "user_id": user_id,
        "scenario_id": scenario["scenario_id"],
        "intent": scenario["intent"],
        "follow_up_strategy": scenario["follow_up_strategy"],
        "expected_complexity": scenario["expected_complexity"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "turns": turns,
        "turn_count": len(turns) // 2,
        "metadata": {
            "persona": user_profile["persona"],
            "max_turns": scenario["max_turns"],
        },
    }


async def harvest_user(
    user_profile: dict,
    limit: int | None,
    resume: bool,
    verbose: bool,
):
    """Run all scenarios for one user."""
    user_id = user_profile["user_id"]
    scenarios = user_profile["scenarios"]
    if limit:
        scenarios = scenarios[:limit]

    user_dir = HISTORY_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)

    # Track errors
    errors = []
    completed = 0
    skipped = 0

    # Create runner and client
    runner = InMemoryRunner(agent=root_agent)
    client = cfg.new_client()

    print(
        f"\n{BOLD}[{user_id}] {user_profile['name']} — {len(scenarios)} scenarios{RESET}"
    )

    for i, scenario in enumerate(scenarios, start=1):
        session_num = int(scenario["scenario_id"].split("_")[-1])
        output_path = user_dir / f"session_{session_num:03d}.json"

        # Skip existing
        if resume and output_path.exists():
            skipped += 1
            continue

        start = time.time()
        try:
            result = await run_scenario(
                user_profile=user_profile,
                scenario=scenario,
                runner=runner,
                user_agent_client=client,
                verbose=verbose,
            )

            output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
            elapsed = time.time() - start
            completed += 1

            status = f"{GREEN}OK{RESET}"
            print(
                f"  {status}  [{user_id}] Session {i}/{len(scenarios)}"
                f" — {scenario['intent']}"
                f" ({result['turn_count']} turns, {elapsed:.1f}s)"
            )

        except Exception as e:  # noqa: BLE001 — record per-session failure and continue harvest
            elapsed = time.time() - start
            errors.append(
                {
                    "scenario_id": scenario["scenario_id"],
                    "error": str(e),
                    "elapsed": elapsed,
                }
            )
            print(
                f"  {RED}ERR{RESET}  [{user_id}] Session {i}/{len(scenarios)}"
                f" — {scenario['intent']}: {e}"
            )

        # Small delay between scenarios to avoid rate limiting
        await asyncio.sleep(0.5)

    # Save errors if any
    if errors:
        errors_path = user_dir / "errors.json"
        errors_path.write_text(json.dumps(errors, indent=2))

    print(
        f"  {BOLD}[{user_id}] Done:{RESET}"
        f" {GREEN}{completed} completed{RESET}"
        + (f", {YELLOW}{skipped} skipped{RESET}" if skipped else "")
        + (f", {RED}{len(errors)} errors{RESET}" if errors else "")
    )

    return completed, skipped, len(errors)


async def async_main(args):
    # Load profiles
    if not PROFILES_PATH.exists():
        print(f"{RED}Error: {PROFILES_PATH} not found.{RESET}")
        print("Run: python user_profiles/generate_profiles.py")
        sys.exit(1)

    profiles = json.loads(PROFILES_PATH.read_text())
    users = profiles["users"]

    # Filter to one user if specified
    if args.user:
        users = [u for u in users if u["user_id"] == args.user]
        if not users:
            print(f"{RED}Error: user '{args.user}' not found in profiles.json{RESET}")
            sys.exit(1)

    total_completed = 0
    total_skipped = 0
    total_errors = 0

    print(f"{BOLD}Harvest — Conversational History Generation{RESET}")
    print(f"  Users:     {len(users)}")
    print(f"  Scenarios: {sum(len(u['scenarios']) for u in users)}")
    if args.limit:
        print(f"  Limit:     {args.limit} per user")

    for user in users:
        c, s, e = await harvest_user(
            user_profile=user,
            limit=args.limit,
            resume=args.resume,
            verbose=args.verbose,
        )
        total_completed += c
        total_skipped += s
        total_errors += e

    total = total_completed + total_skipped + total_errors
    print(f"\n{BOLD}━━━ Harvest Summary ━━━{RESET}")
    print(f"  Completed: {GREEN}{total_completed}/{total}{RESET}")
    if total_skipped:
        print(f"  Skipped:   {YELLOW}{total_skipped}{RESET}")
    if total_errors:
        print(f"  Errors:    {RED}{total_errors}{RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate conversational history via simulated user-assistant conversations"
    )
    parser.add_argument("--user", type=str, help="Run for a specific user only")
    parser.add_argument("--limit", type=int, help="Limit scenarios per user")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Print conversations"
    )
    parser.add_argument("--resume", action="store_true", help="Skip existing sessions")
    args = parser.parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
