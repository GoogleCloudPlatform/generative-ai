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

"""Shared evaluation harness functions.

Extracted from test_augmented_agent.py for reuse in both the final
evaluation (test_augmented_agent.py) and the validation gate
(analyzer/swarm_generator.py).

These functions are framework-agnostic — they work with both ADK agents
(via InMemoryRunner) and raw agent modules (via direct execute() calls).
"""

import json
import re
from pathlib import Path

import config as cfg
from google import genai

# ── Constants ────────────────────────────────────────────────────────────

JUDGE_MODEL = cfg.JUDGE_MODEL
JUDGE_FALLBACK_MODELS = cfg.JUDGE_FALLBACKS
GOAL_REACHED_SIGNAL = "[GOAL_REACHED]"

# ── Simulated user agent ────────────────────────────────────────────────

_EVAL_USER_PROMPT = """\
You are role-playing as a real person with this profile:
{persona}

You are having a conversation with an AI assistant. Your goal is:
{intent}
{goal_section}
This is turn {turn_number} of the conversation. The assistant just said:
---
{assistant_response}
---

IMPORTANT: Decide whether your goal has been FULLY achieved:
- If the assistant's response (combined with all previous responses) gives
  you everything you need to achieve your goal, respond with EXACTLY:
  [GOAL_REACHED]
- If you still need more information, generate your next follow-up message
  using the "{follow_up_strategy}" strategy:
  - "clarify": Ask for more specific detail on one point
  - "deep_dive": Ask to expand on a sub-topic or go deeper
  - "pivot": Shift to a related but different aspect
  - "correct": Redirect — "actually I meant..."

Rules:
- Be realistic about when your goal is met. Don't keep asking if you
  already have what you need.
- But also don't settle for a superficial answer when you need depth.
- Stay in character. Match the persona's communication style.
- Write ONLY the user's next message (or [GOAL_REACHED]). No meta-commentary.
- Keep messages under 100 words.
{style_hints_section}
"""


def build_style_hints(user_style: dict) -> str:
    """Convert user_style.json into behavioral hints for the simulated user.

    These hints make the simulated user react naturally to preference
    matches/mismatches without explicitly stating preferences in messages.
    """
    hints = []
    if user_style.get("format"):
        hints.append(
            f"You prefer {user_style['format']} — if the response "
            f"doesn't match, you might ask a follow-up to get what you need"
        )
    if user_style.get("response_length"):
        hints.append(f"You like responses that are {user_style['response_length']}")
    if user_style.get("avoid"):
        hints.append(f"You find {user_style['avoid']} unhelpful and may disengage")
    if user_style.get("tone"):
        hints.append(f"You respond well to a {user_style['tone']} tone")
    if not hints:
        return ""
    hint_lines = "\n".join(f"- {h}" for h in hints)
    return f"""
Your communication tendencies (behave according to these naturally,
do NOT explicitly state these preferences in your messages):
{hint_lines}

CRITICAL: Do NOT mention these preferences directly. Do NOT say things like
"I prefer concise answers" or "please use bullet points." A real user wouldn't
spell out their preferences every time — they just react naturally when the
response doesn't fit their style (e.g., asking for more specifics, moving on
quickly when satisfied, showing mild frustration with walls of text)."""


async def run_eval_user_turn(
    client: genai.Client,
    persona: str,
    intent: str,
    follow_up_strategy: str,
    assistant_response: str,
    turn_number: int,
    goal_definition: str = "",
    style_hints: str = "",
) -> str | None:
    """Generate the simulated user's next message, or None if goal reached."""
    goal_section = ""
    if goal_definition:
        goal_section = f"\nYour goal is FULLY met when: {goal_definition}\n"

    style_hints_section = style_hints if style_hints else ""

    prompt = _EVAL_USER_PROMPT.format(
        persona=persona,
        intent=intent,
        goal_section=goal_section,
        turn_number=turn_number,
        assistant_response=assistant_response,
        follow_up_strategy=follow_up_strategy,
        style_hints_section=style_hints_section,
    )

    response = await client.aio.models.generate_content(
        model=cfg.EVAL_USER_SIM_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=512,
        ),
    )

    if response.text is None:
        return None  # treat empty response as goal reached
    text = response.text.strip()
    if not text or GOAL_REACHED_SIGNAL in text:
        return None
    return text


# ── Conversation formatting ─────────────────────────────────────────────


def format_conversation(conversation: list[dict]) -> str:
    lines = []
    for turn in conversation:
        role = "User" if turn["role"] == "user" else "Assistant"
        lines.append(f"**{role}:** {turn['content']}")
    return "\n\n".join(lines)


def load_user_style(user_id: str) -> str:
    """Load user_style.json for a user, return formatted text or empty string."""
    style_path = Path(__file__).parent.parent / "swarms" / user_id / "user_style.json"
    if style_path.exists():
        try:
            style = json.loads(style_path.read_text())
            return json.dumps(style, indent=2)
        except (json.JSONDecodeError, OSError):
            pass
    return ""


# ── LLM Judge ────────────────────────────────────────────────────────────


def build_judge_prompt(
    rubric_text: str,
    scenario_info: dict,
    baseline_result: dict | None,
    augmented_result: dict | None,
) -> str:
    sections = []

    if baseline_result:
        sections.append(f"""<baseline_conversation>
Agent: Baseline (no personalization)
Turns: {baseline_result["turn_count"]}
Goal reached: {baseline_result["goal_reached"]}

{format_conversation(baseline_result["turns"])}
</baseline_conversation>""")

    if augmented_result:
        sections.append(f"""<augmented_conversation>
Agent: Augmented (with personalized mini-agent swarm)
Turns: {augmented_result["turn_count"]}
Goal reached: {augmented_result["goal_reached"]}

{format_conversation(augmented_result["turns"])}
</augmented_conversation>""")

    conversations_text = "\n\n".join(sections)

    # Build user preferences section for personalization scoring
    user_style_text = load_user_style(scenario_info.get("user_id", ""))
    if user_style_text:
        _preferences_section = f"""<user_preferences>
These preferences were learned from 50 past conversations with this user.
Use them to evaluate the personalization dimension.
{user_style_text}
</user_preferences>"""
    else:
        _preferences_section = ""

    if baseline_result and augmented_result:
        scoring_instruction = """Score BOTH agents on QUALITY. Return JSON with:
- "baseline": {"accuracy": 1-4, "helpfulness": 1-4, "personalization": 1-4, "justification": "one paragraph"}
- "augmented": {"accuracy": 1-4, "helpfulness": 1-4, "personalization": 1-4, "justification": "one paragraph"}
- "quality_winner": "baseline" | "augmented" | "tie"
- "quality_summary": "one paragraph explaining the quality winner decision"

The quality_winner is determined by averaging all 3 scores for each agent.
Do NOT consider turn count, efficiency, or number of follow-ups in your quality judgment.
Turn burden is evaluated separately and programmatically."""
    else:
        agent_label = "augmented" if augmented_result else "baseline"
        scoring_instruction = f"""Score the {agent_label} agent on QUALITY. Return JSON with:
- "{agent_label}": {{"accuracy": 1-4, "helpfulness": 1-4, "personalization": 1-4, "justification": "one paragraph"}}"""

    return f"""You are a strict evaluator comparing AI assistant responses.
Judge from the perspective of a returning user with known preferences.

The same simulated user drove BOTH conversations with the same opening
message.

## QUALITY EVALUATION

Score each agent on these 3 dimensions:

1. **accuracy** (1-4): Is the response factually correct?
   Any fabrication of facts, URLs, API parameters, or technical details
   -> score = 1.
   4 = fully accurate; 3 = minor inaccuracies; 2 = significant errors; 1 = fabrication

2. **helpfulness** (1-4): Does the response actually solve the user's
   problem? Does it address all parts of the request?
   4 = fully solves the problem; 3 = mostly solves with minor gaps;
   2 = partially addresses; 1 = misses the point

3. **personalization** (1-4): Does the response feel tailored to THIS
   specific user? Consider BOTH proactive intelligence (anticipating needs
   without being asked) AND preference alignment (matching known format,
   tone, detail level). Use the <user_preferences> section below to judge.
   4 = anticipated the user's full workflow AND perfectly matched their preferences;
   3 = included proactive elements OR matched most preferences;
   2 = addressed only the immediate question in a generic way;
   1 = ignored known preferences and missed obvious follow-up needs

Do NOT evaluate turn count, efficiency, or number of follow-ups.
Turn burden is evaluated separately and programmatically.

{scoring_instruction}

<test_info>
Scenario: {scenario_info["name"]}
User intent: {scenario_info["scenario"]["intent"]}
User persona: {scenario_info["persona"]}
</test_info>

{_preferences_section}

{conversations_text}"""


async def judge_conversation(
    scenario_info: dict,
    baseline_result: dict | None,
    augmented_result: dict | None,
    rubric_text: str,
    judge_client: genai.Client,
) -> dict | None:
    """Run LLM judge on conversation results. Returns scores dict or None."""
    from analyzer.llm_util import generate_with_fallback

    prompt = build_judge_prompt(
        rubric_text, scenario_info, baseline_result, augmented_result
    )

    response = await generate_with_fallback(
        client=judge_client,
        model=JUDGE_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=1.0,
            max_output_tokens=8192,
        ),
        fallback_models=JUDGE_FALLBACK_MODELS,
    )

    text = response.text.strip() if response.text else ""
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        result = json.loads(text)
        if isinstance(result, list):
            result = result[0] if result and isinstance(result[0], dict) else None
        return result
    except (json.JSONDecodeError, TypeError):
        cleaned = re.sub(r",\s*([}\]])", r"\1", text)
        try:
            result = json.loads(cleaned)
            if isinstance(result, list):
                result = result[0] if result and isinstance(result[0], dict) else None
            return result
        except (json.JSONDecodeError, TypeError):
            return None
