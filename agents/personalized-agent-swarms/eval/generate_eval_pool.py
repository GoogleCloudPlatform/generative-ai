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

"""Generate a pool of synthetic evaluation test cases from conversation history.

For each user, reads all historic sessions, groups them by intent, and uses an
LLM to synthesize N new test cases per session. The cases preserve the same
intent but use different concrete scenarios.

Output: eval_pool/{user_id}/pool.json

Usage:
    python eval/generate_eval_pool.py                          # all users
    python eval/generate_eval_pool.py --user user_4            # single user
    python eval/generate_eval_pool.py --user user_4 -n 3       # 3 cases/session
    python eval/generate_eval_pool.py --user user_4 --dry-run  # preview only
"""

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import config as cfg
from analyzer.llm_util import generate_with_fallback
from google import genai

# ── Paths ────────────────────────────────────────────────────────────
HISTORY_DIR = Path(__file__).parent.parent / "history"
PROFILES_PATH = Path(__file__).parent.parent / "user_profiles" / "profiles.json"
POOL_DIR = Path(__file__).parent.parent / "eval_pool"

DEFAULT_N_PER_SESSION = 2
DEFAULT_MODEL = cfg.ANALYSIS_MODEL

# ANSI colours
GREEN = "\033[92m"
YELLOW = "\033[93m"
DIM = "\033[2m"
RESET = "\033[0m"

# ── LLM prompt ───────────────────────────────────────────────────────

_SYNTHESIS_PROMPT = """\
You are generating synthetic evaluation test cases for an AI assistant.

Below are {n_sessions} real conversation sessions from user "{user_id}" \
(persona: {persona}). All share the intent "{intent}".

For EACH session, generate {n_per_session} new test cases that:
1. Preserve the SAME intent category ("{intent}")
2. Use a DIFFERENT concrete scenario (different numbers, situations, specifics)
3. Match the user's communication style and expertise level
4. Are plausible for this persona

For each test case return a JSON object with:
- "pool_entry_id": "pool_{user_id_short}_{intent}_NNN" (unique, sequential)
- "source_session_id": the scenario_id of the session you derived this from
- "goal_definition": 1 sentence describing when the user's goal is fully met
- "opening_message": the user's first message (50-150 words, in character)
- "follow_up_strategy": one of "clarify", "deep_dive", "pivot", "correct"
- "max_turns": integer 3-5

CRITICAL:
- Do NOT reuse the exact same scenario, numbers, or phrasing from any source session
- opening_message must test a NEW facet of this intent
- goal_definition must be concrete and verifiable
- Stay in character for the persona

<sessions>
{sessions_json}
</sessions>

Return a JSON array of test case objects. No explanation, just the array.
"""


def _load_profiles() -> dict[str, dict]:
    """Load user profiles from profiles.json. Returns {user_id: profile}."""
    data = json.loads(PROFILES_PATH.read_text())
    return {u["user_id"]: u for u in data["users"]}


def _load_sessions(user_id: str) -> list[dict]:
    """Load all session files for a user."""
    user_dir = HISTORY_DIR / user_id
    if not user_dir.exists():
        return []
    sessions = []
    for f in sorted(user_dir.glob("session_*.json")):
        try:
            sessions.append(json.loads(f.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    return sessions


def _group_by_intent(sessions: list[dict]) -> dict[str, list[dict]]:
    """Group sessions by their intent field."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for s in sessions:
        intent = s.get("intent")
        if not intent:
            continue
        groups[intent].append(s)
    return dict(groups)


def _prepare_session_for_prompt(session: dict) -> dict:
    """Extract the fields relevant for the synthesis prompt."""
    turns = session.get("turns", [])
    first_user_msg = ""
    for t in turns:
        if t.get("role") == "user":
            first_user_msg = t["content"]
            break
    return {
        "scenario_id": session.get("scenario_id", "unknown"),
        "intent": session.get("intent", "unknown"),
        "opening_message": first_user_msg[:500],
        "follow_up_strategy": session.get("follow_up_strategy", "deep_dive"),
        "turn_count": session.get("turn_count", len(turns)),
    }


def _parse_json_lenient(text: str) -> list[dict]:
    """Parse JSON array from LLM output, handling truncation and formatting issues.

    Tries strict parsing first, then attempts repair strategies:
    1. Close unterminated strings and brackets
    2. Extract valid objects individually via regex
    """
    import re

    # Try strict parse first
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            parsed = parsed.get("entries", parsed.get("test_cases", []))
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        pass

    # Strategy 1: Try to close truncated JSON
    # Find where the last complete object ends (last "}")
    repaired = text.rstrip()
    # Close any open strings
    quote_count = repaired.count('"') - repaired.count('\\"')
    if quote_count % 2 == 1:
        repaired += '"'
    # Close any open objects/arrays
    open_braces = repaired.count("{") - repaired.count("}")
    open_brackets = repaired.count("[") - repaired.count("]")
    repaired += "}" * max(0, open_braces)
    repaired += "]" * max(0, open_brackets)

    try:
        parsed = json.loads(repaired)
        if isinstance(parsed, dict):
            parsed = parsed.get("entries", parsed.get("test_cases", []))
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract individual JSON objects via regex
    # Find all {...} blocks that look like valid entries
    entries = []
    for match in re.finditer(r'\{[^{}]*"pool_entry_id"[^{}]*\}', text, re.DOTALL):
        try:
            obj = json.loads(match.group())
            entries.append(obj)
        except json.JSONDecodeError:
            continue

    if entries:
        return entries

    # Strategy 3: Try truncating at the last complete object
    last_brace = text.rfind("}")
    if last_brace > 0:
        truncated = text[: last_brace + 1]
        # Find the opening bracket
        first_bracket = truncated.find("[")
        if first_bracket >= 0:
            truncated = truncated[first_bracket:] + "]"
            try:
                parsed = json.loads(truncated)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

    return []


async def generate_pool_for_intent(
    sessions: list[dict],
    user_id: str,
    persona: str,
    intent: str,
    client: genai.Client,
    n_per_session: int = DEFAULT_N_PER_SESSION,
    model: str = DEFAULT_MODEL,
) -> list[dict]:
    """Generate synthetic test cases for all sessions sharing one intent."""
    prepped = [_prepare_session_for_prompt(s) for s in sessions]
    user_id_short = user_id.replace("user_", "u")

    prompt = _SYNTHESIS_PROMPT.format(
        n_sessions=len(prepped),
        user_id=user_id,
        user_id_short=user_id_short,
        persona=persona,
        intent=intent,
        n_per_session=n_per_session,
        sessions_json=json.dumps(prepped, indent=2),
    )

    response = await generate_with_fallback(
        client=client,
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.4,
            max_output_tokens=8192,
        ),
    )

    text = response.text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    parsed = _parse_json_lenient(text)

    # Ensure each entry has required fields and source_intent
    entries = []
    for entry in parsed:
        entry["source_intent"] = intent
        # Validate required fields
        if not entry.get("opening_message") or not entry.get("goal_definition"):
            continue
        entries.append(entry)

    return entries


async def generate_pool_for_user(
    user_id: str,
    client: genai.Client,
    n_per_session: int = DEFAULT_N_PER_SESSION,
    model: str = DEFAULT_MODEL,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """Generate the full eval pool for one user."""
    profiles = _load_profiles()
    profile = profiles.get(user_id)
    if not profile:
        print(f"  {YELLOW}Warning: no profile for {user_id}, skipping{RESET}")
        return {}

    persona = profile["persona"]
    sessions = _load_sessions(user_id)
    if not sessions:
        print(f"  {YELLOW}Warning: no sessions for {user_id}, skipping{RESET}")
        return {}

    intent_groups = _group_by_intent(sessions)
    print(f"  {user_id}: {len(sessions)} sessions, {len(intent_groups)} intents")

    if dry_run:
        for intent, group in intent_groups.items():
            print(
                f"    {intent}: {len(group)} sessions → {len(group) * n_per_session} synthetic cases"
            )
        expected_total = sum(len(g) * n_per_session for g in intent_groups.values())
        print(f"    Total: {expected_total} entries (dry run, no LLM calls)")
        return {}

    all_entries = []
    for idx, (intent, group) in enumerate(sorted(intent_groups.items()), 1):
        print(
            f"    [{idx}/{len(intent_groups)}] {intent} ({len(group)} sessions)...",
            flush=True,
        )
        try:
            entries = await generate_pool_for_intent(
                sessions=group,
                user_id=user_id,
                persona=persona,
                intent=intent,
                client=client,
                n_per_session=n_per_session,
                model=model,
            )
            all_entries.extend(entries)
            print(f"      {GREEN}→ {len(entries)} cases generated{RESET}")
        except Exception as e:  # noqa: BLE001 — best-effort per-intent LLM generation
            print(f"      {YELLOW}→ failed: {e}{RESET}")

    # Build pool data
    pool = {
        "metadata": {
            "user_id": user_id,
            "persona": persona,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_sessions": len(sessions),
            "n_per_session": n_per_session,
            "total_entries": len(all_entries),
            "intents": sorted(intent_groups.keys()),
            "model": model,
        },
        "entries": all_entries,
    }

    # Write pool file
    pool_user_dir = POOL_DIR / user_id
    pool_user_dir.mkdir(parents=True, exist_ok=True)
    pool_path = pool_user_dir / "pool.json"
    pool_path.write_text(json.dumps(pool, indent=2, ensure_ascii=False))
    print(f"  {GREEN}Wrote {len(all_entries)} entries → {pool_path}{RESET}")

    return pool


async def async_main():
    parser = argparse.ArgumentParser(
        description="Generate eval pool from conversation history"
    )
    parser.add_argument("--user", type=str, help="Single user to process (e.g. user_4)")
    parser.add_argument(
        "-n",
        type=int,
        default=DEFAULT_N_PER_SESSION,
        help=f"Synthetic cases per session (default: {DEFAULT_N_PER_SESSION})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"LLM model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without making LLM calls"
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    client = cfg.new_client()

    if args.user:
        user_ids = [args.user]
    else:
        # Discover all users from history/
        user_ids = sorted(
            d.name
            for d in HISTORY_DIR.iterdir()
            if d.is_dir() and d.name.startswith("user_")
        )

    print(f"Generating eval pool ({args.n} cases/session, model: {args.model})")
    print(f"Users: {user_ids}\n")

    for user_id in user_ids:
        await generate_pool_for_user(
            user_id=user_id,
            client=client,
            n_per_session=args.n,
            model=args.model,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        print()


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
