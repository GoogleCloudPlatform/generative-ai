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

"""Sample evaluation scenarios from the pre-generated eval pool.

Reads the pool for a user, maps pool entries to generated agents via
intent-to-agent keyword matching, then uses an LLM review step to confirm
that selected cases would realistically trigger (or not trigger) the agents.

Output: evaluation_scenarios_{user_id}.json (same format as test harness expects)

Usage:
    python eval/sample_eval_scenarios.py                           # all users
    python eval/sample_eval_scenarios.py --user user_4             # single user
    python eval/sample_eval_scenarios.py --user user_4 --total 20  # 20 scenarios
    python eval/sample_eval_scenarios.py --user user_4 --seed 42   # reproducible
    python eval/sample_eval_scenarios.py --user user_4 --skip-review  # no LLM review
"""

import argparse
import asyncio
import json
import random
import sys
from pathlib import Path

import numpy as np

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import config as cfg
from analyzer.llm_util import generate_with_fallback
from google import genai

# ── Paths ────────────────────────────────────────────────────────────
POOL_DIR = Path(__file__).parent.parent / "eval_pool"
SWARMS_DIR = Path(__file__).parent.parent / "swarms"
PROFILES_PATH = Path(__file__).parent.parent / "user_profiles" / "profiles.json"
OUTPUT_DIR = Path(__file__).parent.parent  # evaluation_scenarios_{user_id}.json

DEFAULT_TOTAL = 20
REVIEW_MODEL = cfg.REVIEW_MODEL  # higher quality for review accuracy

# ANSI colours
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
RESET = "\033[0m"

# ── Out-of-domain fallback scenarios ─────────────────────────────────
# Used when all pool intents map to some agent (no "not relevant" entries).
_OUT_OF_DOMAIN_INTENTS = [
    {
        "intent": "python_programming",
        "goal_definition": "Get help with a basic programming question.",
        "opening_message": "My nephew asked me to help with his Python homework. He needs to write a program that sorts a list of numbers. I have no idea about coding. Can you explain it simply?",
        "follow_up_strategy": "clarify",
        "max_turns": 3,
    },
    {
        "intent": "car_repair",
        "goal_definition": "Get advice on whether to repair or replace and approximate costs.",
        "opening_message": "My car has been making a weird rattling noise from the engine area when I accelerate. It's a 2016 Honda Civic with 95K miles. Should I be worried? Is this something I can check myself?",
        "follow_up_strategy": "clarify",
        "max_turns": 3,
    },
    {
        "intent": "gardening",
        "goal_definition": "Get practical gardening advice with a planting plan.",
        "opening_message": "I want to start growing vegetables in my backyard. I have a 10x10 patch that gets about 6 hours of sun. What should I plant for a beginner? I'm in Zone 6.",
        "follow_up_strategy": "clarify",
        "max_turns": 3,
    },
    {
        "intent": "parenting",
        "goal_definition": "Get practical advice for the described parenting situation.",
        "opening_message": "My 10-year-old has been struggling with math and is starting to say he hates school. His teacher says he's capable but just doesn't try. How do I motivate him without adding pressure?",
        "follow_up_strategy": "clarify",
        "max_turns": 3,
    },
    {
        "intent": "home_improvement",
        "goal_definition": "Get a practical DIY plan with materials and steps.",
        "opening_message": "I want to repaint my bedroom. The walls have some nail holes and a few small cracks. What's the right prep work and what type of paint should I use? I've never painted a room before.",
        "follow_up_strategy": "deep_dive",
        "max_turns": 3,
    },
    {
        "intent": "astronomy",
        "goal_definition": "Get a clear explanation of an astronomy concept.",
        "opening_message": "My kid asked me why the moon changes shape during the month. I know it has to do with the sun but I can't explain it clearly. Can you help me understand lunar phases so I can explain it to a 7-year-old?",
        "follow_up_strategy": "clarify",
        "max_turns": 3,
    },
    {
        "intent": "pet_care",
        "goal_definition": "Get practical pet care advice.",
        "opening_message": "I'm thinking about getting a cat. I've never had a pet before. What are the basics I need to know — costs, supplies, vet visits? I live in a small apartment.",
        "follow_up_strategy": "clarify",
        "max_turns": 3,
    },
    {
        "intent": "fitness",
        "goal_definition": "Get a beginner workout plan.",
        "opening_message": "I want to start exercising but I'm completely out of shape. I can't run for more than 2 minutes. What's a realistic plan to build up fitness over the next 3 months? I have no gym membership.",
        "follow_up_strategy": "deep_dive",
        "max_turns": 3,
    },
]


# ── LLM review prompt ───────────────────────────────────────────────

_REVIEW_PROMPT = """\
You are reviewing candidate evaluation test cases for an AI agent trigger system.

The system has specialized mini-agents that activate when a user message matches \
their domain. You need to judge whether each candidate message would realistically \
trigger the specified agent — or for "not relevant" candidates, confirm that NO \
agent should fire.

## Available agents and their descriptions:
{agents_summary}

## Candidates to review:
{candidates_json}

For each candidate, return a JSON object with:
- "id": the candidate's pool_entry_id
- "verdict": "accept" or "reject"
- "best_agent": the agent name most likely to trigger (or null if none should)
- "reason": 1 sentence why

Return a JSON array. No explanation outside the array.
"""


# ── Intent-to-agent matching (coarse, keyword-based) ─────────────────


def _intent_matches_agent(
    intent: str,
    agent_name: str,
    trigger_config: dict,
) -> bool:
    """Check if a session intent is semantically covered by an agent.

    Uses substring matching to handle stemming variants
    (e.g., 'troubleshoot' matches 'troubleshooting').
    """
    intent_words = set(intent.lower().replace("-", "_").split("_"))
    intent_words.discard("")

    if not intent_words:
        return False

    scope_words: set[str] = set()
    scope_words.update(agent_name.lower().split("_"))

    desc = trigger_config.get("description", "")
    scope_words.update(w.lower().strip(".,;:()") for w in desc.split())

    rules = trigger_config.get("rules", {})
    keywords = rules.get("require_any_keyword", [])
    for kw in keywords:
        scope_words.update(kw.lower().split())

    # Substring matching: handles stemming (troubleshoot/troubleshooting,
    # configure/configuration) without a full stemmer.
    for iw in intent_words:
        if len(iw) < 3:
            # Short words (ci, cd) need exact match to avoid false positives
            if iw in scope_words:
                return True
        else:
            for sw in scope_words:
                if len(sw) < 3:
                    continue
                if iw in sw or sw in iw:
                    return True

    return False


def build_intent_agent_map(
    triggers: dict,
    intents: list[str],
) -> dict[str, list[str]]:
    """Map each intent to the list of agents whose triggers match it."""
    mapping: dict[str, list[str]] = {}
    for intent in intents:
        matched = []
        for agent_name, config in triggers.items():
            if agent_name == "_config":
                continue
            if _intent_matches_agent(intent, agent_name, config):
                matched.append(agent_name)
        mapping[intent] = matched
    return mapping


# ── Embedding-based intent matching ───────────────────────────────────


async def _embedding_intent_agent_map(
    entries: list[dict],
    triggers: dict,
    client: genai.Client,
    threshold: float = 0.35,
) -> dict[str, list[str]]:
    """Map intents to agents using embedding similarity on opening messages.

    For each unique intent, embeds a representative opening message and
    compares against all agents' scope_embeddings.  More robust than keyword
    matching as it handles paraphrasing and stemming naturally.

    Uses a lower threshold (0.35) than runtime matching because the goal
    here is classification (relevant vs not-relevant), not agent selection.
    """
    # Collect agent scope embeddings
    agent_embeddings = {}
    for name, trig in triggers.items():
        if name == "_config":
            continue
        emb = trig.get("scope_embedding")
        if emb:
            agent_embeddings[name] = np.array(emb, dtype=np.float32)

    if not agent_embeddings:
        return {}

    # Pick one representative message per intent
    intent_messages: dict[str, str] = {}
    for entry in entries:
        intent = entry["source_intent"]
        if intent not in intent_messages:
            intent_messages[intent] = entry["opening_message"][:2000]

    intents = list(intent_messages.keys())
    messages = [intent_messages[i] for i in intents]

    # Batch embed
    try:
        embed_resp = await client.aio.models.embed_content(
            model=cfg.EMBED_MODEL,
            contents=messages,
        )
    except Exception as e:  # noqa: BLE001 — best-effort embedding call, degrade gracefully
        print(f"    {YELLOW}Embedding intent matching failed: {e}{RESET}")
        return {}

    # Score each intent against each agent
    mapping: dict[str, list[str]] = {}
    for i, intent in enumerate(intents):
        msg_emb = np.array(embed_resp.embeddings[i].values, dtype=np.float32)
        matched = []
        for agent_name, agent_emb in agent_embeddings.items():
            sim = float(
                np.dot(msg_emb, agent_emb)
                / (np.linalg.norm(msg_emb) * np.linalg.norm(agent_emb) + 1e-9)
            )
            if sim >= threshold:
                matched.append((agent_name, sim))
        matched.sort(key=lambda x: x[1], reverse=True)
        mapping[intent] = [name for name, _ in matched]

    return mapping


# ── LLM review ───────────────────────────────────────────────────────


def _build_agents_summary(triggers: dict) -> str:
    """Build a concise summary of all agents for the review prompt."""
    lines = []
    for name, config in triggers.items():
        if name == "_config":
            continue
        desc = config.get("description", "No description")
        rules = config.get("rules", {})
        keywords = rules.get("require_any_keyword", [])
        kw_str = ", ".join(keywords[:10]) if keywords else "none"
        lines.append(f"- **{name}**: {desc}\n  Keywords: {kw_str}")
    return "\n".join(lines)


async def _llm_review_candidates(
    relevant_candidates: list[tuple[dict, list[str]]],
    not_relevant_candidates: list[dict],
    triggers: dict,
    client: genai.Client,
) -> tuple[list[tuple[dict, str]], list[dict]]:
    """Use LLM to review and filter candidate eval cases.

    Returns:
        (confirmed_relevant, confirmed_not_relevant)
        - confirmed_relevant: list of (entry, best_agent_name)
        - confirmed_not_relevant: list of entries
    """
    agents_summary = _build_agents_summary(triggers)

    # Build candidates list for the prompt
    candidates = []
    for entry, agents in relevant_candidates:
        candidates.append(
            {
                "pool_entry_id": entry["pool_entry_id"],
                "opening_message": entry["opening_message"][:300],
                "proposed_agent": agents[0] if agents else None,
            }
        )
    for entry in not_relevant_candidates:
        candidates.append(
            {
                "pool_entry_id": entry["pool_entry_id"],
                "opening_message": entry["opening_message"][:300],
            }
        )

    if not candidates:
        return [], []

    # Batch into chunks of 20 to stay within token limits
    batch_size = 20
    all_verdicts: dict[str, dict] = {}

    for i in range(0, len(candidates), batch_size):
        batch = candidates[i : i + batch_size]
        prompt = _REVIEW_PROMPT.format(
            agents_summary=agents_summary,
            candidates_json=json.dumps(batch, indent=2),
        )

        try:
            response = await generate_with_fallback(
                client=client,
                model=REVIEW_MODEL,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                    max_output_tokens=2048,
                ),
            )

            text = response.text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                text = "\n".join(lines)

            verdicts = json.loads(text)
            if isinstance(verdicts, dict):
                verdicts = verdicts.get("verdicts", verdicts.get("candidates", []))

            for v in verdicts:
                all_verdicts[v["id"]] = v

        except Exception as e:  # noqa: BLE001 — best-effort LLM review, fail open
            print(
                f"    {YELLOW}LLM review batch failed: {e} — accepting all in batch{RESET}"
            )
            # On failure, accept all candidates in this batch
            for c in batch:
                all_verdicts[c["pool_entry_id"]] = {
                    "id": c["pool_entry_id"],
                    "verdict": "accept",
                    "best_agent": c.get("proposed_agent"),
                }

    # Partition results
    confirmed_relevant = []
    confirmed_not_relevant = []

    accepted = 0
    rejected = 0

    for entry, agents in relevant_candidates:
        pid = entry["pool_entry_id"]
        verdict = all_verdicts.get(pid, {})
        if verdict.get("verdict") == "reject":
            rejected += 1
            continue
        # Use LLM's best_agent if provided, otherwise fall back to keyword match
        best_agent = verdict.get("best_agent") or (agents[0] if agents else None)
        if best_agent:
            confirmed_relevant.append((entry, best_agent))
            accepted += 1

    for entry in not_relevant_candidates:
        pid = entry["pool_entry_id"]
        verdict = all_verdicts.get(pid, {})
        if verdict.get("verdict") == "reject":
            # LLM thinks this WOULD trigger an agent — skip it
            rejected += 1
            continue
        if verdict.get("best_agent"):
            # LLM found a matching agent — not truly "not relevant"
            rejected += 1
            continue
        confirmed_not_relevant.append(entry)
        accepted += 1

    print(f"    LLM review: {accepted} accepted, {rejected} rejected")

    return confirmed_relevant, confirmed_not_relevant


# ── Core sampler ─────────────────────────────────────────────────────


def load_pool(user_id: str) -> dict:
    """Load the eval pool for a user."""
    pool_path = POOL_DIR / user_id / "pool.json"
    if not pool_path.exists():
        raise FileNotFoundError(
            f"No pool found at {pool_path}. "
            f"Run: python eval/generate_eval_pool.py --user {user_id}"
        )
    return json.loads(pool_path.read_text())


def load_triggers(user_id: str) -> dict:
    """Load triggers.json for a user's swarm."""
    triggers_path = SWARMS_DIR / user_id / "triggers.json"
    if not triggers_path.exists():
        raise FileNotFoundError(
            f"No swarm found at {triggers_path}. Run swarm generation first."
        )
    return json.loads(triggers_path.read_text())


def _get_persona(user_id: str) -> str:
    """Get persona string from profiles or pool metadata."""
    if PROFILES_PATH.exists():
        profiles = json.loads(PROFILES_PATH.read_text())
        for u in profiles["users"]:
            if u["user_id"] == user_id:
                return u["persona"]
    return ""


async def _validate_expected_agents(
    scenarios: list[dict],
    triggers: dict,
    client: genai.Client,
) -> list[dict]:
    """Cross-check expected_swarm_agent against actual embedding scores.

    For each similar scenario, embeds the opening_message and scores it
    against all agents' scope_embeddings. If the highest-scoring agent
    differs from expected_swarm_agent, adds a _validation_warning.
    """
    similar = [s for s in scenarios if s.get("should_trigger_swarm")]
    if not similar:
        return scenarios

    # Batch embed all opening messages
    messages = [s["opening_message"][:2000] for s in similar]
    try:
        embed_resp = await client.aio.models.embed_content(
            model=cfg.EMBED_MODEL,
            contents=messages,
        )
    except Exception as e:  # noqa: BLE001 — best-effort embedding call, degrade gracefully
        print(f"    {YELLOW}Embedding validation failed: {e}{RESET}")
        return scenarios

    # Collect agent embeddings
    agent_embeddings = {}
    for name, trig in triggers.items():
        if name == "_config":
            continue
        emb = trig.get("scope_embedding")
        if emb:
            agent_embeddings[name] = np.array(emb, dtype=np.float32)

    if not agent_embeddings:
        return scenarios

    warnings = 0
    for i, sc in enumerate(similar):
        msg_emb = np.array(embed_resp.embeddings[i].values, dtype=np.float32)

        best_agent, best_score = None, -1.0
        for name, agent_emb in agent_embeddings.items():
            dot = float(np.dot(msg_emb, agent_emb))
            norm = float(np.linalg.norm(msg_emb) * np.linalg.norm(agent_emb) + 1e-9)
            sim = dot / norm
            if sim > best_score:
                best_agent, best_score = name, sim

        expected = sc.get("expected_swarm_agent")
        if best_agent and best_agent != expected:
            sc["_validation_warning"] = (
                f"Expected {expected} but embedding best match is "
                f"{best_agent} (score={best_score:.3f})"
            )
            print(
                f"    {YELLOW}Warning [{sc['scenario_id']}]: "
                f"expected {expected}, embedding says {best_agent} "
                f"(score={best_score:.3f}){RESET}"
            )
            warnings += 1

    if warnings:
        print(
            f"    {YELLOW}{warnings} scenario(s) have expected_agent "
            f"mismatches vs embedding scores{RESET}"
        )
    else:
        print(f"    {GREEN}All expected_agents validated against embeddings{RESET}")

    return scenarios


async def sample_scenarios(
    user_id: str,
    total: int = DEFAULT_TOTAL,
    seed: int | None = None,
    skip_review: bool = False,
    client: genai.Client | None = None,
) -> dict:
    """Sample balanced eval scenarios from the pool.

    Steps:
    1. Load pool + triggers, build keyword-based intent-agent map
    2. Partition pool into relevant / not-relevant candidates
    3. Oversample candidates (3x the needed count)
    4. LLM review: filter candidates to keep only confirmed matches
    5. Sample final set from confirmed candidates

    Returns the complete evaluation scenarios dict.
    """
    pool_data = load_pool(user_id)
    triggers = load_triggers(user_id)
    persona = pool_data["metadata"].get("persona", _get_persona(user_id))

    entries = pool_data["entries"]
    unique_intents = sorted({e["source_intent"] for e in entries})

    # Step 1: Intent → agent mapping
    # Primary: embedding similarity (robust, handles paraphrasing)
    # Fallback: substring keyword matching (when client unavailable)
    if client:
        intent_map = await _embedding_intent_agent_map(entries, triggers, client)
        # Merge with keyword fallback for any intents embeddings missed
        keyword_map = build_intent_agent_map(triggers, unique_intents)
        for intent in unique_intents:
            if not intent_map.get(intent):
                intent_map[intent] = keyword_map.get(intent, [])
    else:
        intent_map = build_intent_agent_map(triggers, unique_intents)

    # Step 2: Partition
    relevant_entries = []
    not_relevant_entries = []

    for entry in entries:
        intent = entry["source_intent"]
        agents = intent_map.get(intent, [])
        if agents:
            relevant_entries.append((entry, agents))
        else:
            not_relevant_entries.append(entry)

    # Print mapping info
    print("  Intent → agent mapping (keyword-based):")
    for intent in unique_intents:
        agents = intent_map.get(intent, [])
        tag = (
            f"{GREEN}matched {', '.join(agents)}{RESET}"
            if agents
            else f"{DIM}(no agent){RESET}"
        )
        count = sum(1 for e in entries if e["source_intent"] == intent)
        print(f"    {intent} ({count} cases) → {tag}")

    print(
        f"  Pool: {len(relevant_entries)} relevant, {len(not_relevant_entries)} not-relevant"
    )

    n_similar = total // 2
    n_different = total - n_similar
    rng = random.Random(seed)

    if not skip_review and client:
        # Step 3: Oversample candidates (3x to have room after filtering)
        oversample_relevant = min(n_similar * 3, len(relevant_entries))
        oversample_not_relevant = min(n_different * 3, len(not_relevant_entries))

        candidate_relevant = rng.sample(relevant_entries, oversample_relevant)
        candidate_not_relevant = (
            rng.sample(not_relevant_entries, oversample_not_relevant)
            if not_relevant_entries
            else []
        )

        # Step 4: LLM review
        print(
            f"  Running LLM review on {len(candidate_relevant)} relevant + "
            f"{len(candidate_not_relevant)} not-relevant candidates..."
        )

        confirmed_relevant, confirmed_not_relevant = await _llm_review_candidates(
            candidate_relevant,
            candidate_not_relevant,
            triggers,
            client,
        )

        print(
            f"  After review: {len(confirmed_relevant)} relevant, "
            f"{len(confirmed_not_relevant)} not-relevant confirmed"
        )

        # Step 5: Sample from confirmed
        if len(confirmed_relevant) < n_similar:
            print(
                f"  {YELLOW}Warning: only {len(confirmed_relevant)} confirmed relevant, "
                f"requested {n_similar}{RESET}"
            )
            n_similar = len(confirmed_relevant)
            n_different = total - n_similar

        sampled_relevant = rng.sample(
            confirmed_relevant, min(n_similar, len(confirmed_relevant))
        )
        sampled_not_relevant_raw = confirmed_not_relevant

    else:
        # No LLM review — use keyword matching directly
        if len(relevant_entries) < n_similar:
            print(
                f"  {YELLOW}Warning: only {len(relevant_entries)} relevant entries, "
                f"requested {n_similar}{RESET}"
            )
            n_similar = len(relevant_entries)
            n_different = total - n_similar

        sampled_relevant_pairs = rng.sample(
            relevant_entries, min(n_similar, len(relevant_entries))
        )
        sampled_relevant = [
            (e, rng.choice(agents)) for e, agents in sampled_relevant_pairs
        ]
        sampled_not_relevant_raw = not_relevant_entries

    # Sample not-relevant
    sampled_not_relevant = []
    if len(sampled_not_relevant_raw) >= n_different:
        sampled_not_relevant = rng.sample(sampled_not_relevant_raw, n_different)
    else:
        sampled_not_relevant = list(sampled_not_relevant_raw)
        shortfall = n_different - len(sampled_not_relevant)
        if shortfall > 0:
            print(f"  {YELLOW}Using {shortfall} out-of-domain fallback(s){RESET}")
            available_ood = list(_OUT_OF_DOMAIN_INTENTS)
            rng.shuffle(available_ood)
            for ood in available_ood[:shortfall]:
                sampled_not_relevant.append(
                    {
                        "pool_entry_id": f"ood_{user_id}_{ood['intent']}",
                        "source_session_id": None,
                        "source_intent": ood["intent"],
                        "goal_definition": ood["goal_definition"],
                        "opening_message": ood["opening_message"],
                        "follow_up_strategy": ood["follow_up_strategy"],
                        "max_turns": ood["max_turns"],
                    }
                )

    # Build output scenarios
    scenarios = []
    user_short = user_id.replace("user_", "u")

    # Similar scenarios
    for idx, (entry, agent) in enumerate(sampled_relevant, 1):
        scenarios.append(
            {
                "scenario_id": f"eval_{user_short}_sim_{idx:03d}",
                "category": "similar",
                "intent": entry["source_intent"],
                "expected_swarm_agent": agent,
                "should_trigger_swarm": True,
                "goal_definition": entry["goal_definition"],
                "opening_message": entry["opening_message"],
                "follow_up_strategy": entry.get("follow_up_strategy", "deep_dive"),
                "max_turns": entry.get("max_turns", 4),
            }
        )

    # Different scenarios
    for idx, entry in enumerate(sampled_not_relevant, 1):
        scenarios.append(
            {
                "scenario_id": f"eval_{user_short}_diff_{idx:03d}",
                "category": "different",
                "intent": entry.get("source_intent", entry.get("intent", "unknown")),
                "expected_swarm_agent": None,
                "should_trigger_swarm": False,
                "goal_definition": entry["goal_definition"],
                "opening_message": entry["opening_message"],
                "follow_up_strategy": entry.get("follow_up_strategy", "clarify"),
                "max_turns": entry.get("max_turns", 3),
            }
        )

    # Validate expected_agents against embedding scores
    if client:
        print("  Validating expected_agents against embeddings...")
        scenarios = await _validate_expected_agents(scenarios, triggers, client)

    result = {
        "metadata": {
            "description": f"Auto-generated evaluation scenarios for {user_id}.",
            "total_scenarios": len(scenarios),
            "similar_scenarios": len(sampled_relevant),
            "different_scenarios": len(scenarios) - len(sampled_relevant),
            "user_id": user_id,
            "persona": persona,
            "generated_from_pool": True,
            "llm_reviewed": not skip_review,
            "seed": seed,
        },
        "scenarios": scenarios,
    }

    return result


async def async_main():
    parser = argparse.ArgumentParser(
        description="Sample evaluation scenarios from the eval pool"
    )
    parser.add_argument("--user", type=str, help="Single user (e.g. user_4)")
    parser.add_argument(
        "--total",
        type=int,
        default=DEFAULT_TOTAL,
        help=f"Total scenarios to sample (default: {DEFAULT_TOTAL})",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--skip-review",
        action="store_true",
        help="Skip LLM review (use keyword matching only)",
    )
    args = parser.parse_args()

    client = None
    if not args.skip_review:
        client = cfg.new_client()

    if args.user:
        user_ids = [args.user]
    else:
        if not POOL_DIR.exists():
            print(
                f"{RED}No eval_pool/ directory. Run generate_eval_pool.py first.{RESET}"
            )
            sys.exit(1)
        user_ids = sorted(
            d.name
            for d in POOL_DIR.iterdir()
            if d.is_dir() and d.name.startswith("user_")
        )

    review_label = "skip-review" if args.skip_review else "with LLM review"
    print(
        f"Sampling eval scenarios (total={args.total}, seed={args.seed}, {review_label})"
    )
    print(f"Users: {user_ids}\n")

    for user_id in user_ids:
        print(f"{user_id}:")
        try:
            result = await sample_scenarios(
                user_id=user_id,
                total=args.total,
                seed=args.seed,
                skip_review=args.skip_review,
                client=client,
            )
        except FileNotFoundError as e:
            print(f"  {RED}{e}{RESET}")
            continue

        # Write output
        out_path = OUTPUT_DIR / f"evaluation_scenarios_{user_id}.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        n_sim = result["metadata"]["similar_scenarios"]
        n_diff = result["metadata"]["different_scenarios"]
        print(
            f"  {GREEN}Wrote {n_sim} similar + {n_diff} different → {out_path.name}{RESET}\n"
        )


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
