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

"""Analyze conversation history and generate mini-agent swarms.

Reads session logs from history/, extracts patterns, and generates
personalized mini-agent swarms to swarms/.

Usage:
    python analyzer/analyze_history.py
    python analyzer/analyze_history.py --user user_1
    python analyzer/analyze_history.py --user user_1 --dry-run
    python analyzer/analyze_history.py --verbose
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from google import genai

sys.path.insert(0, str(Path(__file__).parent.parent))
import config as cfg
from analyzer.pattern_extractor import extract_patterns
from analyzer.swarm_generator import generate_swarm

HISTORY_DIR = Path(__file__).parent.parent / "history"
SWARMS_DIR = Path(__file__).parent.parent / "swarms"

# ANSI colours
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


async def analyze_user(
    user_id: str,
    client: genai.Client,
    dry_run: bool,
    verbose: bool,
    skip_critic: bool = False,
):
    """Analyze one user's history and generate their swarm."""
    user_history_dir = HISTORY_DIR / user_id
    if not user_history_dir.exists():
        print(f"  {RED}No history found for {user_id}{RESET}")
        return

    # Load all sessions
    sessions = []
    for session_file in sorted(user_history_dir.glob("session_*.json")):
        sessions.append(json.loads(session_file.read_text()))

    print(f"  Loaded {len(sessions)} sessions for {user_id}")

    if not sessions:
        print(f"  {YELLOW}No sessions to analyze{RESET}")
        return

    # Extract patterns
    print("  Extracting patterns...")
    patterns = await extract_patterns(sessions, user_id, client)
    task_patterns = [p for p in patterns if p.pattern_type == "task"]
    behavioral_patterns = [p for p in patterns if p.pattern_type == "behavioral"]
    print(
        f"  Found {GREEN}{len(patterns)} patterns{RESET} (frequency >= 3)"
        f" — {len(task_patterns)} task, {len(behavioral_patterns)} behavioral"
    )

    if verbose or dry_run:
        for p in patterns:
            type_label = (
                f"{DIM}[behavioral]{RESET}" if p.pattern_type == "behavioral" else ""
            )
            print(
                f"    {YELLOW}•{RESET} {p.pattern_name}"
                f" (freq={p.frequency}, {p.complexity})"
                f" {type_label}"
                f": {p.description}"
            )
            if verbose:
                print(f"      Triggers: {', '.join(p.trigger_signals[:6])}")
                print(f"      Flow: {' → '.join(p.typical_flow[:4])}")
                prefs = json.dumps(p.user_preferences, ensure_ascii=False)
                print(
                    f"      Preferences: {prefs[:120]}{'...' if len(prefs) > 120 else ''}"
                )

    if dry_run:
        print(f"  {DIM}Dry run — skipping swarm generation{RESET}")
        return

    # Generate swarm
    print("  Generating swarm...")
    manifest = await generate_swarm(
        patterns,
        user_id,
        SWARMS_DIR,
        client,
        skip_critic=skip_critic,
    )
    absorbed = manifest.get("behavioral_patterns_absorbed", 0)
    style_note = f", {absorbed} behavioral → user_style.json" if absorbed else ""
    print(
        f"  {GREEN}Generated swarm:{RESET} {manifest['agent_count']} agents{style_note}"
        f" → swarms/{user_id}/"
    )

    # Print critic results
    critic = manifest.get("critic_pass")
    if critic and not critic.get("skipped"):
        revised = critic.get("agents_revised", 0)
        trig_rev = critic.get("triggers_revised", 0)
        total = critic.get("total_agents", 0)
        print(
            f"  {GREEN}Critic pass:{RESET} {revised}/{total} agents revised"
            f", {trig_rev} triggers revised"
        )
        if verbose:
            for d in critic.get("details", []):
                status = d.get("status", "unknown")
                score = d.get("score", "?")
                issues = d.get("issues", [])
                color = GREEN if status == "passed" else YELLOW
                print(f"    {color}•{RESET} {d['agent']} (score={score}, {status})")
                for issue in issues[:3]:
                    print(f"      {DIM}— {issue}{RESET}")
    elif skip_critic:
        print(f"  {DIM}Critic pass: skipped (--skip-critic){RESET}")

    # Print ranking results
    ranking = manifest.get("ranking_pass")
    if ranking and not ranking.get("skipped"):
        selected = ranking.get("selected", [])
        dropped = ranking.get("dropped", [])
        fallback = ranking.get("fallback", False)
        method = "frequency-only fallback" if fallback else "LLM-ranked"
        print(
            f"  {GREEN}Ranking pass ({method}):{RESET} kept {len(selected)}, "
            f"dropped {len(dropped)}: {dropped}"
        )
        if verbose and not fallback:
            for r in ranking.get("rankings", []):
                vetoed = r.get("vetoed", False)
                if vetoed:
                    status = f"VETOED — {r.get('veto_reason', '?')}"
                else:
                    status = f"rank={r.get('rank')}"
                total = r.get("weighted_total", "?")
                name = r.get("agent_name", "?")
                in_selected = name in selected
                color = GREEN if in_selected else DIM
                print(f"    {color}•{RESET} {name} (total={total}, {status})")
    elif ranking and ranking.get("skipped"):
        reason = ranking.get("reason", "")
        print(f"  {DIM}Ranking pass: skipped ({reason}){RESET}")


async def async_main(args):
    # Discover users from history/
    if args.user:
        user_ids = [args.user]
    else:
        user_ids = sorted(
            d.name
            for d in HISTORY_DIR.iterdir()
            if d.is_dir() and d.name.startswith("user_")
        )

    if not user_ids:
        print(f"{RED}No user histories found in {HISTORY_DIR}{RESET}")
        print("Run: python harvest/orchestrator.py")
        sys.exit(1)

    client = cfg.new_client()

    print(f"{BOLD}Analyzer — Pattern Extraction & Swarm Generation{RESET}")
    print(f"  Users: {', '.join(user_ids)}")
    print(
        f"  Model: {' → '.join([cfg.ANALYSIS_MODEL, *cfg.ANALYSIS_FALLBACKS])} (location={cfg.LOCATION})"
    )
    if args.dry_run:
        print(f"  Mode:  {YELLOW}DRY RUN{RESET}")
    print()

    for user_id in user_ids:
        print(f"\n{BOLD}[{user_id}]{RESET}")
        await analyze_user(
            user_id=user_id,
            client=client,
            dry_run=args.dry_run,
            verbose=args.verbose,
            skip_critic=args.skip_critic,
        )

    if not args.dry_run:
        print(f"\n{BOLD}━━━ Analysis Complete ━━━{RESET}")
        print(f"  Swarms written to: {SWARMS_DIR}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze conversation history and generate mini-agent swarms"
    )
    parser.add_argument("--user", type=str, help="Analyze a specific user only")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show patterns without generating agents"
    )
    parser.add_argument(
        "--skip-critic", action="store_true", help="Skip critic/revision pass"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Detailed output")
    args = parser.parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
