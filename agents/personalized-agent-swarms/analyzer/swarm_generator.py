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

"""Generate mini-agent swarms from extracted patterns.

For each pattern, creates:
1. A trigger definition (attribute-match with structured rules)
2. A Python agent file with an async execute() function
3. A user_style.json from behavioral patterns (applied to all agents)

Behavioral patterns (how the user communicates) are separated from task
patterns (what the user wants) and aggregated into a shared style profile
instead of becoming standalone agents.

Trigger rules are generated via an LLM pass that produces structured
domain/task_type/keyword rules for programmatic matching at runtime.
"""

import asyncio
import importlib.util
import json
import math
import re
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import config as cfg
from analyzer.pattern_extractor import Pattern
from google import genai

# ── Agent selection constants ─────────────────────────────────────────
HARD_CAP_AGENTS = 30  # Safety cap: prevent runaway cost on extreme cases
MIN_QUALITY_SCORE = 25  # Minimum weighted total (out of 50) to keep an agent
MERGE_OVERLAP_THRESHOLD = 0.73  # Pairwise overlap above this triggers LLM merge review
VALIDATION_MIN_QUALITY = (
    2.5  # Min avg quality score (1-4) on validation similar scenarios
)
VALIDATION_MAX_FALSE_POSITIVES = (
    1  # Max false positives on validation different scenarios (out of 3)
)


def _extract_json(text: str) -> dict:
    """Extract and parse JSON from LLM response text.

    Handles markdown fences (```json ... ```), trailing commas,
    unquoted keys, and common LLM JSON formatting issues.
    Raises json.JSONDecodeError or TypeError if all extraction attempts fail.
    """
    if text is None:
        raise TypeError("response text is None")
    text = text.strip()
    if not text:
        raise json.JSONDecodeError("empty response", text, 0)

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    fence_match = re.search(r"```(?:\w*)\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # First attempt: parse as-is
    try:
        result = json.loads(text)
        return result
    except json.JSONDecodeError:
        pass

    # Second attempt: remove trailing commas before } or ]
    cleaned = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Third attempt: fix unquoted keys ({value: 4} → {"value": 4})
    fixed = re.sub(r"(?<=[{,])\s*(\w+)\s*:", r' "\1":', cleaned)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Fourth attempt: regex field extraction for critic/judge JSON
    score_match = re.search(r'"(?:agent_)?score"\s*:\s*(\d+)', text)
    pass_match = re.search(r'"(?:agent_)?pass"\s*:\s*(true|false)', text, re.IGNORECASE)
    if score_match:
        issues = []
        issues_match = re.search(
            r'"(?:agent_)?issues"\s*:\s*\[(.*?)\]', text, re.DOTALL
        )
        if issues_match:
            issues = [
                s.strip().strip('"')
                for s in issues_match.group(1).split(",")
                if s.strip()
            ]
        issues.append("JSON parse recovered via regex")
        return {
            "agent_pass": pass_match is not None
            and pass_match.group(1).lower() == "true",
            "agent_score": int(score_match.group(1)),
            "agent_issues": issues,
            "trigger_pass": True,
        }

    # All attempts failed — raise for caller to handle
    raise json.JSONDecodeError("all JSON extraction attempts failed", text, 0)


_USER_STYLE_PROMPT = """\
You are analyzing a user's communication patterns to build a style profile.

## Behavioral patterns (HOW the user communicates):
{behavioral_patterns}

## Task patterns (WHAT the user asks for — use these to avoid contradictions):
{task_pattern_summaries}

Synthesize into a JSON object with these keys:
- response_length: how long responses should be. IMPORTANT: if the user's
  task patterns show they request comprehensive/detailed output, do NOT
  set this to "short" or "concise" just because they sometimes feel
  overwhelmed. Instead, say something like "comprehensive but well-structured
  with clear headers and sections".
- language_level: vocabulary complexity
- format: preferred structure (e.g., "structured with headers and bullet
  points", "tables and frameworks")
- tone: communication tone
- follow_up: how to handle next steps
- avoid: things the user genuinely dislikes. IMPORTANT: if the user gets
  overwhelmed by long responses but still explicitly asks for detailed
  frameworks, the problem is formatting not length. Put "unstructured walls
  of text" NOT "long responses" or "comprehensive frameworks".

Return ONLY the JSON object, no explanation.
"""

_AGENT_GEN_PROMPT = """\
You are generating a specialized mini-agent Python module for a user's
recurring task pattern.

Pattern details:
- Name: {pattern_name}
- Description: {description}
- Typical flow: {typical_flow}
- User preferences: {user_preferences}
- Complexity: {complexity}

User communication style (apply to ALL responses from this agent):
{user_style}

Generate a complete Python module. Follow this EXACT structure:

For STATIC agents (complexity == "static"):
```python
\"\"\"Mini-agent: {pattern_name}
Auto-generated from {user_id}'s conversational history.
{description}
\"\"\"

AGENT_META = {{
    "name": "{pattern_name}",
    "description": "{description}",
    "complexity": "static",
    "source_sessions": {frequency},
}}

ENRICHED_PROMPT = \"\"\"
[Prompt structure (keep under 100 words / 10 lines):
- Role identity (1 sentence)
- Key user preferences as bullet points (3-5 bullets)
- {{user_message}} and {{history}} placeholders
- Output format instructions (1-2 lines)
The prompt tells the LLM WHAT to produce, not HOW to think.
Include: "Conversation so far: {{history}}" for context.
NEVER include instructions to detect incomplete messages or ask
for clarification — always answer the user's message directly.]
\"\"\"

from google.genai import types

async def execute(user_message: str, llm_client, history: list[dict] | None = None) -> str:
    if history:
        history_context = "Conversation so far:\\n" + "\\n".join(
            f"{{t['role'].upper()}}: {{t['content']}}" for t in history[-6:]
        )
    else:
        history_context = "Note: This is the FIRST message in this conversation. There is no prior context. Do not reference any previous discussion."
    prompt = ENRICHED_PROMPT.format(user_message=user_message, history=history_context)
    response = await llm_client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=65536, thinking_config=types.ThinkingConfig(thinking_budget=2048)),
    )
    return response.text
```

For DYNAMIC agents (complexity == "dynamic"):
```python
\"\"\"Mini-agent: {pattern_name}
Auto-generated from {user_id}'s conversational history.
{description}
\"\"\"

from google.genai import types

AGENT_META = {{
    "name": "{pattern_name}",
    "description": "{description}",
    "complexity": "dynamic",
    "source_sessions": {frequency},
}}

STEPS = [
    {{
        "name": "step_1_draft",
        "prompt": \"\"\"[Step 1 prompt — draft the response. Keep under 10 lines.
Include {{user_message}}, {{previous_output}}, and {{history}} placeholders.
Embed user preferences directly. Only step 1 uses {{history}}.
NEVER ask for clarification — always process the message directly.]\"\"\",
    }},
    # For TECHNICAL domains (software_engineering, devops, database,
    # cloud_infrastructure), add this verification step:
    # {{
    #     "name": "step_2_verify",
    #     "prompt": \"\"\"Review the draft for factual accuracy:
    # - Check API names and parameters actually exist
    # - Check code syntax is correct
    # - Check configuration values and CLI flags are valid
    # - Add "verify this" caveats for uncertain claims
    # Fix any issues found. Return the corrected draft.
    # Draft: {{previous_output}}
    # Original request: {{user_message}}\"\"\",
    # }},
    # For NON-TECHNICAL domains, omit the verification step.
    {{
        "name": "step_final",
        "prompt": \"\"\"[Final step — synthesize all previous outputs into the
complete response. Include {{user_message}} and {{previous_output}}.
This step produces the FINAL output returned to the user.]\"\"\",
    }},
    # 2-3 steps. Technical domains: draft → verify → format.
    # Non-technical: draft → synthesize. execute() returns ONLY the last step's output.
]

async def execute(user_message: str, llm_client, history: list[dict] | None = None) -> str:
    if history:
        history_context = "Conversation so far:\\n" + "\\n".join(
            f"{{t['role'].upper()}}: {{t['content']}}" for t in history[-6:]
        )
    else:
        history_context = "Note: This is the FIRST message in this conversation. There is no prior context. Do not reference any previous discussion."
    outputs = []
    for i, step in enumerate(STEPS):
        prompt = step["prompt"].format(
            user_message=user_message,
            previous_output="\\n".join(outputs)[:6000],
            history=history_context if i == 0 else "",
        )
        response = await llm_client.aio.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=65536, thinking_config=types.ThinkingConfig(thinking_budget=2048)),
        )
        outputs.append(response.text)
    return outputs[-1]
```

{anti_patterns}

Rules:
- Return ONLY the Python code, no markdown fences, no explanation.
- The execute() function must be async and accept (user_message: str, llm_client, history: list[dict] | None = None).
- CRITICAL: use this exact async call pattern:
    await llm_client.aio.models.generate_content(model="gemini-3-flash-preview", contents=prompt, config=types.GenerateContentConfig(max_output_tokens=65536, thinking_config=types.ThinkingConfig(thinking_budget=2048)))
  Do NOT use generate_content_async — that method does not exist.
  Always include `from google.genai import types` at the top of the module.
- For STATIC agents: ENRICHED_PROMPT must be under 150 words / 12 lines.
  The extra budget allows domain-specific accuracy guardrails (e.g., "only use
  Dockerfile instructions you are certain exist").
- For DYNAMIC agents: each step prompt must be under 100 words / 10 lines.
- Embed the user's specific preferences as bullet points.
- Match the user's preferred detail level — if the user likes detailed responses, do NOT
  add "keep it concise" or "be brief" instructions to the prompt.
- NEVER include instructions to detect incomplete/cut-off messages or ask the user for
  clarification. The agent must always answer directly, even if the input seems incomplete.
- Dynamic agents with technical domains (software_engineering, devops, database,
  cloud_infrastructure) should use 3 steps: draft → verify accuracy → format.
  Non-technical dynamic agents use 2 steps: process → synthesize.
  execute() returns ONLY the last step's output.
- IMPORTANT: At the end of ENRICHED_PROMPT (or the first step's prompt for dynamic agents),
  add this line: "Note: These agent-specific instructions take precedence over any
  STYLE INSTRUCTIONS injected at runtime." This ensures the agent's domain-specific tone
  and format requirements override generic user style preferences when they conflict.
- IMPORTANT: Always wrap code output in markdown ``` fences with the appropriate language
  tag (e.g., ```python, ```dockerfile, ```sql). Never output raw unfenced code. Add this
  instruction to the ENRICHED_PROMPT or final step prompt.
- Never add conversational follow-ups like "Is there anything else I can help with?" or
  "Let me know if you need more help" unless the user explicitly asks.
- NEVER use "progressive disclosure", "one topic at a time", "bite-sized", or "offer to
  dive deeper" in agent prompts. These cause the agent to drip-feed answers over multiple
  turns instead of providing a complete response. The agent MUST deliver a full answer in
  one turn.
- Do NOT hardcode specific tool names, platforms, or technologies in prompts. Use generic
  references like "the platform/tool the user mentioned" so the agent adapts to the
  actual request instead of biasing toward one technology.
- When the topic may involve legal, financial, health, or safety matters, include this
  instruction in the prompt: "Include appropriate caveats and recommend professional
  consultation for legal, financial, or regulatory questions."

## Quality checklist (the agent will be evaluated on these)
The generated agent will be scored on 3 dimensions. Optimize for all three:
1. ACCURACY — response must be factually correct. Add a self-verification
   instruction in the prompt: "Double-check technical claims, API names, and
   version numbers before responding. Never fabricate URLs or parameters."
2. HELPFULNESS — response must fully solve the user's request, not just
   discuss it. Include actionable output (code, config, commands) not just
   explanations. The user should be able to act on the response immediately.
3. PERSONALIZATION — response must feel tailored to THIS user. Apply the
   user style profile strictly. Anticipate the user's next steps based on
   their known workflow patterns — deliver the full outcome proactively,
   don't wait for follow-up questions.

## GROUNDING RULE (critical for accuracy)
Only reference APIs, CLI flags, functions, and configuration options that are
well-documented and widely known. If uncertain about exact syntax or parameter
names, the agent prompt MUST include a caveat like "verify the exact flag name"
rather than fabricating. Add this instruction to ENRICHED_PROMPT (or the first
step prompt for dynamic agents): "If you are not 100% certain a specific API,
CLI flag, or parameter exists, say so explicitly rather than guessing."
"""


_DISAMBIGUATE_PROMPT = """\
You are refining trigger descriptions for a set of specialized mini-agents
belonging to the same user. Each description tells an LLM screener when
to activate that agent.

Problem: some agents cover overlapping domains, so their descriptions
must be precise enough that a screener can distinguish them.

For each agent below, rewrite its description to be:
1. Specific about what it DOES handle
2. Explicit about what it does NOT handle (add "NOT X" clauses where
   another agent covers a related topic)
3. One paragraph, 2-4 sentences max

Return a JSON object mapping agent_name -> refined_description.

Agents:
{agents_text}
"""


async def _generate_user_style(
    behavioral_patterns: list[Pattern],
    task_patterns: list[Pattern],
    client: genai.Client,
    model: str,
) -> dict:
    """Synthesize behavioral patterns into a user communication style profile.

    Also considers task patterns to avoid contradictions (e.g., user gets
    overwhelmed but explicitly asks for comprehensive frameworks).

    Args:
        behavioral_patterns: Patterns classified as "behavioral".
        task_patterns: Patterns classified as "task" (for context).
        client: Google Cloud genai client.
        model: Model for synthesis.

    Returns:
        Style profile dict with keys like response_length, tone, etc.
    """
    if not behavioral_patterns:
        return {}

    patterns_text = "\n".join(
        f"- {p.pattern_name} (frequency={p.frequency}): {p.description}\n"
        f"  User preferences: {json.dumps(p.user_preferences)}"
        for p in behavioral_patterns
    )
    task_summaries = (
        "\n".join(
            f"- {p.pattern_name} (frequency={p.frequency}): {p.description} "
            f"[detail_level={p.user_preferences.get('detail_level', 'N/A')}, "
            f"format={p.user_preferences.get('format', 'N/A')}]"
            for p in task_patterns
        )
        if task_patterns
        else "No task patterns available."
    )
    prompt = _USER_STYLE_PROMPT.format(
        behavioral_patterns=patterns_text,
        task_pattern_summaries=task_summaries,
    )

    from analyzer.llm_util import generate_with_fallback

    response = await generate_with_fallback(
        client=client,
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=1024,
        ),
    )

    try:
        return _extract_json(response.text)
    except (json.JSONDecodeError, TypeError):
        # Fallback: extract basics from the behavioral patterns directly
        return {
            "response_length": "concise, 3-5 paragraphs max",
            "language_level": "simple, accessible",
            "format": "direct answer first",
            "tone": "warm, patient",
            "follow_up": "one concrete next step",
            "avoid": "long frameworks, walls of text",
        }


async def _fact_check_agent(
    agent_code: str,
    pattern,
    client,
    model: str,
) -> str:
    """Scan generated agent code for potentially fabricated technical claims.

    Extracts ENRICHED_PROMPT (or STEPS prompts) and asks an LLM to flag
    any specific API names, CLI flags, URLs, or technical details that
    may be fabricated. If LOW-confidence claims are found, revises the
    prompt to add uncertainty caveats.
    """
    from analyzer.llm_util import generate_with_fallback

    # Extract prompt content from generated code
    prompt_match = re.search(
        r'ENRICHED_PROMPT\s*=\s*"""(.*?)"""',
        agent_code,
        re.DOTALL,
    )
    if not prompt_match:
        # Try STEPS format
        prompt_match = re.search(
            r'"prompt"\s*:\s*"""(.*?)"""',
            agent_code,
            re.DOTALL,
        )
    if not prompt_match:
        return agent_code  # can't extract prompt, skip

    prompt_content = prompt_match.group(1)

    check_prompt = (
        "Review this agent prompt for factual claims. List any specific "
        "API names, CLI flags, URLs, function names, or technical details "
        "that may be fabricated or incorrect.\n\n"
        f"Agent domain: {pattern.description}\n\n"
        f"Prompt content:\n{prompt_content}\n\n"
        "For each claim found, rate confidence:\n"
        "- HIGH: well-known, widely documented\n"
        "- MEDIUM: plausible but should be verified\n"
        "- LOW: likely fabricated or doesn't exist\n\n"
        'Return JSON: {"claims": [{"claim": "...", "confidence": "HIGH|MEDIUM|LOW"}]}\n'
        'If no specific technical claims found, return: {"claims": []}'
    )

    try:
        resp = await generate_with_fallback(
            client=client,
            model=model,
            contents=check_prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2048,
            ),
        )

        result = _extract_json(resp.text)
        claims = result.get("claims", [])
        low_claims = [c for c in claims if c.get("confidence") == "LOW"]

        if not low_claims:
            return agent_code

        # Revise: add uncertainty caveats for LOW-confidence claims
        low_list = ", ".join(c.get("claim", "") for c in low_claims)
        revise_prompt = (
            f"The following claims in the agent prompt may be fabricated: {low_list}\n\n"
            f"Original prompt:\n{prompt_content}\n\n"
            "Revise the prompt to either:\n"
            "1. Remove the specific fabricated claim, OR\n"
            "2. Add a caveat like 'verify the exact parameter name' next to uncertain claims\n\n"
            "Return ONLY the revised prompt text (no code fences, no explanation)."
        )

        revise_resp = await generate_with_fallback(
            client=client,
            model=model,
            contents=revise_prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2048,
            ),
        )

        revised_prompt = revise_resp.text.strip()
        if revised_prompt:
            agent_code = agent_code.replace(prompt_content, revised_prompt)

    except Exception as e:  # noqa: BLE001 — fact-check is best-effort, don't block generation
        print(f"      Fact-check skipped: {e}", flush=True)

    return agent_code


def _create_trigger(pattern: Pattern) -> dict:
    """Create an attribute-match trigger with initial data from the pattern."""
    return {
        "trigger_type": "attribute_match",
        "rules": {
            "require_any_keyword": pattern.trigger_signals[:15],
        },
        "description": pattern.description,
    }


async def _generate_attribute_rules(
    triggers: dict[str, dict],
    patterns_by_name: dict[str, Pattern],
    client: genai.Client,
    model: str,
) -> dict[str, dict]:
    """Generate structured attribute rules for all agents in one LLM call.

    Uses each pattern's description, trigger_signals, and context_hints
    to produce domain/task_type/keyword/exclusion rules for programmatic
    matching at runtime.
    """
    from analyzer.trigger_schema import build_attribute_rules_prompt, validate_rules

    agents_text = "\n".join(
        f"- {name}: {t['description']}\n"
        f"  Keywords: {', '.join(patterns_by_name[name].trigger_signals[:10])}\n"
        f"  Context: {', '.join(patterns_by_name[name].trigger_context_hints[:8])}"
        for name, t in triggers.items()
        if name in patterns_by_name
    )

    prompt = build_attribute_rules_prompt(agents_text)

    from analyzer.llm_util import generate_with_fallback

    response = await generate_with_fallback(
        client=client,
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=4096,
        ),
    )

    try:
        rules_map = _extract_json(response.text)
    except (json.JSONDecodeError, TypeError):
        print("  Warning: failed to parse attribute rules — keeping initial rules")
        return triggers

    # Merge LLM-generated rules into triggers
    for name, rules in rules_map.items():
        if name in triggers and isinstance(rules, dict):
            # Validate rules
            errors = validate_rules(rules)
            if errors:
                print(f"  Warning: {name} rules have issues: {errors}")
            triggers[name]["rules"] = rules
            triggers[name]["trigger_type"] = "attribute_match"

    return triggers


async def _generate_binary_questions(
    triggers: dict[str, dict],
    patterns_by_name: dict[str, Pattern],
    client: genai.Client,
    model: str,
) -> dict[str, dict]:
    """Generate binary yes/no questions for two-stage matching.

    One LLM call generates contrastive questions for all agents.
    Questions are stored in triggers[agent_name]["binary_questions"].
    """
    from analyzer.llm_util import generate_with_fallback
    from analyzer.trigger_schema import build_binary_questions_prompt

    agents_text = "\n".join(
        f"- {name}: {t['description']}\n"
        f"  Keywords: {', '.join(patterns_by_name[name].trigger_signals[:10])}"
        for name, t in triggers.items()
        if name in patterns_by_name
    )

    prompt = build_binary_questions_prompt(agents_text)

    response = await generate_with_fallback(
        client=client,
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=4096,
        ),
    )

    try:
        questions_map = _extract_json(response.text)
    except (json.JSONDecodeError, TypeError):
        print("  Warning: failed to parse binary questions — skipping")
        return triggers

    # Merge questions into triggers
    for name, questions in questions_map.items():
        if name in triggers and isinstance(questions, list):
            # Validate format
            valid_questions = []
            for q in questions:
                if (
                    isinstance(q, dict)
                    and "question" in q
                    and q.get("expected_answer") in ("yes", "no")
                ):
                    valid_questions.append(q)
            if valid_questions:
                triggers[name]["binary_questions"] = valid_questions

    q_count = sum(
        1
        for name in triggers
        if name != "_config" and triggers[name].get("binary_questions")
    )
    print(f"  Generated binary questions for {q_count} agents")

    return triggers


# Keep old disambiguate for backward compatibility if needed
async def _disambiguate_triggers(
    triggers: dict[str, dict],
    client: genai.Client,
    model: str,
) -> dict[str, dict]:
    """Legacy: refine trigger descriptions with NOT clauses.

    Kept for backward compatibility but no longer called by default.
    Use _generate_attribute_rules instead.
    """
    agents_text = "\n".join(
        f"- {name}: {t['description']}" for name, t in triggers.items()
    )
    prompt = _DISAMBIGUATE_PROMPT.format(agents_text=agents_text)

    from analyzer.llm_util import generate_with_fallback

    response = await generate_with_fallback(
        client=client,
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=4096,
        ),
    )

    try:
        refined = _extract_json(response.text)
    except (json.JSONDecodeError, TypeError):
        return triggers

    for name, new_desc in refined.items():
        if name in triggers and isinstance(new_desc, str):
            triggers[name]["description"] = new_desc

    return triggers


def _resolve_complexity(pattern: Pattern, user_style: dict) -> str:
    """Decide whether an agent should be static or dynamic.

    Overrides pattern.complexity to 'static' when user style signals
    that multi-step workflows are unwanted, or when the typical flow
    is simple enough that a single LLM call suffices.
    """
    avoid = (user_style.get("avoid") or "").lower()
    fmt = (user_style.get("format") or "").lower()

    # User explicitly dislikes multi-step outputs
    anti_dynamic_avoid = any(
        phrase in avoid
        for phrase in [
            "step-by-step",
            "multi-phase",
            "multi-step",
            "phased",
            "framework",
            "stages",
        ]
    )
    # User prefers direct/complete answers
    pro_static_format = any(
        phrase in fmt
        for phrase in [
            "direct answer",
            "complete answer",
            "all at once",
            "single response",
            "one response",
        ]
    )

    if anti_dynamic_avoid or pro_static_format:
        return "static"

    # Simple flow: 2 or fewer steps, no iterative signals
    flow = pattern.typical_flow
    if isinstance(flow, list) and len(flow) <= 2:
        iterative_signals = {"refine", "iterate", "revise", "loop", "feedback"}
        flow_text = " ".join(str(s) for s in flow).lower()
        if not any(sig in flow_text for sig in iterative_signals):
            return "static"

    return pattern.complexity


def _sanitize_user_style(user_style: dict) -> dict:
    """Remove style instructions that cause harmful agent behavior.

    Mini-agents must deliver complete answers in one call. User style
    preferences like "ask for confirmation" or "detect cut-off messages"
    are appropriate for interactive chat but catastrophic for one-shot
    agent execution.
    """
    if not user_style:
        return user_style

    sanitized = dict(user_style)

    # Phrases to strip from all style values
    harmful_phrases = [
        "cut off",
        "cut-off",
        "incomplete",
        "finish their thought",
        "complete their sentence",
        "complete their thought",
        "finish their sentence",
        "unfinished",
        # Paraphrases found in actual user_style.json files
        "inferred completion",
        "infer completion",
        "intent is unclear",
        "intent cannot be",
        "prematurely",
        "premature",
        "accidental send",
        "accidental submission",
        "gentle nudge",
        "gently nudge",
        "nudge inviting",
        "nudge them",
        "fragmented input",
        "incomplete thought",
        "continue their",
        "wait for the user",
    ]

    confirm_phrases = [
        "ask for confirmation before proceeding",
        "ask for confirmation",
        "confirm before proceeding",
    ]

    for key in list(sanitized.keys()):
        val = sanitized[key]
        if not isinstance(val, str):
            continue
        for phrase in harmful_phrases:
            # Remove sentences containing the phrase
            sentences = val.split(". ")
            sentences = [s for s in sentences if phrase not in s.lower()]
            val = ". ".join(sentences)
        # Strip "ask for confirmation" from ALL keys (not just follow_up)
        for confirm_phrase in confirm_phrases:
            val = val.replace(
                confirm_phrase, "provide the complete answer in one response"
            )
            val = val.replace(
                confirm_phrase.capitalize(),
                "Provide the complete answer in one response",
            )
        # Replace fragmentation phrases that cause multi-turn chunking
        fragmentation_phrases = [
            "bite-sized",
            "bite sized",
            "one concept at a time",
            "1-2 paragraphs",
            "1-2 short paragraphs",
            "short paragraphs maximum",
            "chunked delivery",
            "step-by-step chunked",
            "check for understanding",
            "pause to check",
        ]
        for frag in fragmentation_phrases:
            if frag in val.lower():
                val = val.lower().replace(frag, "structured sections")
        # Remove "avoid" entries that suppress comprehensive output
        if key == "avoid":
            suppress_phrases = [
                "long comprehensive lists",
                "exhaustive details",
                "multi-part responses",
                "walls of text",
            ]
            for sp in suppress_phrases:
                if sp in val.lower():
                    val = val.lower().replace(sp, "").strip(", ")
        sanitized[key] = val

    # Global override: ensure all agents deliver complete answers
    sanitized["_global_override"] = (
        "Always provide a complete, direct, self-contained answer. "
        "Never ask the user to finish their thought or complete their message."
    )

    return sanitized


def _generate_anti_pattern_instructions(user_style: dict) -> str:
    """Convert user style 'avoid' items into explicit NEVER instructions."""
    avoid = user_style.get("avoid", "")
    follow_up = user_style.get("follow_up", "")
    lines = []

    # Always prohibit incomplete message detection — this causes false positives
    lines.append(
        "- NEVER include logic to detect incomplete or cut-off messages. "
        "NEVER ask the user to 'complete their thought' or 'finish their sentence'. "
        "Always answer the message as-is, inferring intent if needed."
    )

    # Prohibit micro-chunking — agents must deliver complete answers
    lines.append(
        "- NEVER ask 'Does this make sense?' or 'Shall I continue?' or "
        "'Does this first step make sense?' — always provide a complete, "
        "self-contained answer in one response. Do NOT chunk the response "
        "across multiple turns or ask for confirmation before continuing."
    )

    if avoid:
        items = [a.strip() for a in avoid.split(",")]
        for item in items:
            if item:
                lines.append(f"- NEVER produce {item}")

    if follow_up:
        lines.append(
            f"- For follow-up/next steps: {follow_up}. "
            "Do NOT leave the response incomplete expecting the user to ask for more."
        )

    return "## Anti-patterns (AVOID these in generated agent output)\n" + "\n".join(
        lines
    )


def _generate_domain_criteria(user_style: dict, pattern: Pattern) -> str:
    """Generate domain-specific evaluation criteria for the critic."""
    lang_level = (user_style.get("language_level") or "").lower()
    desc = (pattern.description or "").lower()

    is_technical = any(
        kw in desc
        for kw in [
            "code",
            "api",
            "docker",
            "deploy",
            "debug",
            "architect",
            "database",
            "infrastructure",
            "devops",
            "test",
            "refactor",
        ]
    ) or any(kw in lang_level for kw in ["technical", "expert", "advanced"])

    if is_technical:
        return (
            "Domain: TECHNICAL\n"
            "- Prioritize accuracy and correctness of technical content\n"
            "- Code examples should be runnable and well-structured\n"
            "- Depth of explanation should match the user's expertise level\n"
            "- Prefer concrete solutions over abstract recommendations"
        )
    return (
        "Domain: CONSUMER/GENERAL\n"
        "- Prioritize persona alignment and natural tone\n"
        "- Advice should be actionable and specific, not generic\n"
        "- Response length should match the user's typical preference\n"
        "- Avoid unnecessary jargon or overly formal structure"
    )


_CRITIC_PROMPT = """\
You are a quality critic for auto-generated AI mini-agents. Your job is to
ensure the agent produces output that matches the USER'S STYLE PREFERENCES
and delivers high-quality, complete responses.

## Test scenario
User message: "{test_message}"

## Agent output (what the generated agent produced)
{agent_output}

## Gold references (real conversations with this user — context only, do NOT
require matching their exact format or structure)
{gold_response}

## User communication style profile
{user_style}

## User pattern preferences
{pattern_preferences}

## Domain evaluation criteria
{domain_criteria}

## Current trigger description
Agent name: {agent_name}
Trigger: {trigger_description}

## Original agent code
```python
{agent_code}
```

## Your task

Evaluate the agent output against the USER'S STYLE PREFERENCES (not the gold
reference format). The gold references show what topics and depth this user
cares about, but the agent should follow the user's style profile above.

Evaluation criteria:

1. **COMPLETENESS**: Does the response fully address the user's request?
   A truncated or cut-off response is a critical failure. The response should
   feel finished and self-contained.
2. **STYLE ALIGNMENT**: Does the response match the user's style profile?
   Check response_length, language_level, format, tone, and follow_up
   preferences. The style profile is the authority, not the gold reference.
3. **ANTI-PATTERN AVOIDANCE**: Does the response avoid things listed in the
   user's "avoid" preferences? (e.g., walls of text, multi-phase frameworks,
   excessive jargon)
4. **CONTENT QUALITY**: Does it address the core question with substantive,
   actionable advice rather than vague "let me know if you need more" padding?
   CRITICAL: If the agent asks the user to "complete their thought" or "finish
   their sentence" instead of answering, this is a critical failure (score 0).
   The agent must ALWAYS answer directly, even if the input seems incomplete.
5. **TRUNCATION**: Is the response complete? Check for mid-sentence breaks,
   missing closing sections, or abrupt endings. If truncated, this is a
   critical issue requiring revision.
6. **TRIGGER FIT**: Would the trigger description correctly match the test
   message? Is it too broad (would match unrelated topics) or too narrow?
7. **ACCURACY VERIFICATION**: Does the agent's prompt include any mechanism
   to prevent fabrication? (e.g., "verify before responding", "only reference
   real APIs/tools"). If the output contains fabricated URLs, API names, or
   technical details, this is a critical failure (score 0).
8. **PROACTIVE COMPLETENESS**: Does the agent anticipate the user's next
   steps based on their known workflow patterns? A response that only answers
   the immediate question when the user historically needs follow-up steps
   should lose points.
9. **FACTUAL CROSS-CHECK**: Compare the agent output against the gold
   references on TECHNICAL CLAIMS ONLY. List any specific claims in the
   agent output (API names, parameters, CLI flags, configuration syntax,
   version numbers, code constructs) that contradict the gold reference
   or appear fabricated. For each questionable claim, rate confidence:
   HIGH (likely correct), MEDIUM (plausible but unverified), LOW (likely
   fabricated or contradicts gold reference).

   Any LOW-confidence claim is a critical accuracy issue. If 2+ claims
   are LOW, score the agent 0 for this criterion.

Return a JSON object with these fields:
{{
  "agent_pass": true if agent output quality is acceptable (score >= 7), false otherwise,
  "agent_score": 0-10 (10 = excellent quality aligned with user preferences),
  "agent_issues": ["issue1", "issue2"],
  "factual_issues": ["claim: confidence_level — explanation", ...],
  "trigger_pass": true if trigger description correctly matches this message type,
  "trigger_issue": "description of problem" or null,
  "revised_code": "COMPLETE revised Python module if agent_pass is false, null if pass",
  "revised_trigger_description": "revised description if trigger_pass is false, null if pass"
}}

CRITICAL rules for revised_code:
- Return the COMPLETE Python module (docstring, AGENT_META, STEPS/ENRICHED_PROMPT, execute function)
- The execute() function MUST be async and accept (user_message: str, llm_client, history: list[dict] | None = None)
- Use this exact API: await llm_client.aio.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
- Do NOT use generate_content_async — it does not exist
- Make the output match the USER'S STYLE PREFERENCES, not the reference session
- Do NOT add "check for understanding" or "ready to proceed?" steps unless
  the gold reference explicitly shows the user wants that
- Keep ENRICHED_PROMPT under 150 words for static agents, 100 words per step for dynamic agents
- Add config=types.GenerateContentConfig(max_output_tokens=65536, thinking_config=types.ThinkingConfig(thinking_budget=2048)) to LLM calls
  (include `from google.genai import types` at the top of the module)
- For dynamic agents: 2 steps for non-technical domains, up to 3 steps for technical domains (step 2 = verify accuracy). Return only outputs[-1]
"""


_CRITIC_EVALUATE_PROMPT = """\
You are a quality critic for auto-generated AI mini-agents. Evaluate the agent
output — do NOT produce revised code.

## Test scenario
User message: "{test_message}"

## Agent output
{agent_output}

## Gold references (context only)
{gold_response}

## User communication style profile
{user_style}

## User pattern preferences
{pattern_preferences}

## Domain evaluation criteria
{domain_criteria}

## Agent info
Agent name: {agent_name}
Trigger: {trigger_description}
{truncation_warning}

## Your task

Score the agent output on these 10 criteria:
1. COMPLETENESS — fully addresses the request? Only flag as failure if the
   TRUNCATION WARNING section explicitly says the output was truncated.
2. STYLE ALIGNMENT — matches user style profile?
3. ANTI-PATTERN AVOIDANCE — avoids user's "avoid" preferences?
4. CONTENT QUALITY — substantive, actionable advice? Asking user to "complete thought" = score 0.
5. TRUNCATION — ONLY flag if the TRUNCATION WARNING section explicitly mentions
   truncation. If the output ends with "[... OUTPUT CLIPPED FOR EVALUATION"]
   that is NOT truncation — it means the full response was too long to include
   here but completed successfully. Ignore clipping markers when scoring.
6. TRIGGER FIT — trigger description correctly matches this message type?
7. HALLUCINATION — does the output fabricate context? References to prior
   conversations that didn't happen ("as we discussed", "continuing from",
   "your message was cut off"), invented quotes from the user, or claims
   about user statements that don't appear in the test message = critical
   failure (score 0). Also check for legally dangerous advice presented
   without appropriate caveats.
8. ACCURACY VERIFICATION — does the agent's prompt include any mechanism to
   prevent fabrication? If the output contains fabricated URLs, API names, or
   technical details, this is a critical failure (score 0).
9. PROACTIVE COMPLETENESS — does the agent anticipate the user's next steps
   based on their known workflow patterns? A response that only answers the
   immediate question when the user historically needs follow-up steps should
   lose points.
10. FACTUAL CROSS-CHECK — compare the agent output against the gold
    references on TECHNICAL CLAIMS ONLY. List any specific claims (API names,
    parameters, CLI flags, configuration syntax, version numbers, code
    constructs) that contradict the gold reference or appear fabricated.
    Rate each: HIGH (likely correct), MEDIUM (plausible), LOW (likely
    fabricated). 2+ LOW claims = score 0 for this criterion.

HARD SCORING CONSTRAINT: If the agent output fabricates ANY specific API names,
CLI flags, function signatures, URLs, or package names that do not exist,
agent_score MUST be <= 3 regardless of other criteria. Fabrication cannot be
offset by good style or completeness.

Return JSON:
{{
  "agent_pass": true if score >= 7,
  "agent_score": 0-10,
  "agent_issues": ["issue1", ...],
  "factual_issues": ["claim: confidence_level — explanation", ...],
  "factual_contradictions": <number of LOW-confidence claims that contradict gold reference or are fabricated>,
  "trigger_pass": true if trigger is correct,
  "trigger_issue": "problem description" or null,
  "revised_trigger_description": "revised description if trigger_pass is false" or null
}}

Return ONLY the JSON. No revised code.
"""


_CRITIC_REVISE_PROMPT = """\
You are revising an auto-generated AI mini-agent to fix quality issues.

## Issues to fix
{issues}

## Original agent code
```python
{agent_code}
```

## User communication style profile
{user_style}

## User pattern preferences
{pattern_preferences}

## Test message that exposed the issues
"{test_message}"

## Gold references (context only, do NOT copy format)
{gold_response}
{truncation_warning}

## Your task

Produce a COMPLETE revised Python module that fixes the listed issues.

Rules:
- Return ONLY the Python code, no markdown fences, no explanation.
- The execute() function MUST be async and accept (user_message: str, llm_client, history: list[dict] | None = None).
- Use: await llm_client.aio.models.generate_content(model="gemini-3-flash-preview", contents=prompt, config=types.GenerateContentConfig(max_output_tokens=65536, thinking_config=types.ThinkingConfig(thinking_budget=2048)))
- Do NOT use generate_content_async — it does not exist.
- Include `from google.genai import types` at the top.
- Keep ENRICHED_PROMPT under 150 words for static agents, 100 words per step for dynamic agents.
- For dynamic agents: 2 steps for non-technical domains, up to 3 steps for technical domains (step 2 = verify accuracy). Return only outputs[-1].
- Match the USER'S STYLE PREFERENCES, not the gold reference format.
"""


def _find_best_sessions(
    sessions: list[dict], pattern: Pattern, top_n: int = 3
) -> list[dict]:
    """Find the top N sessions whose first user turn best matches a pattern.

    Uses word overlap between the message and the pattern's trigger signals.
    Returns up to top_n sessions sorted by score descending, or [sessions[0]]
    if no sessions match.
    """
    if not sessions:
        return []

    signals = {s.lower() for s in pattern.trigger_signals}
    if not signals:
        # Fallback: use words from the description
        signals = set(pattern.description.lower().split())

    scored = []
    for session in sessions:
        turns = session.get("turns", [])
        if not turns or turns[0].get("role") != "user":
            continue
        msg_words = set(turns[0]["content"].lower().split())
        score = len(msg_words & signals)
        scored.append((score, session))

    scored.sort(key=lambda x: x[0], reverse=True)

    result = [s for _, s in scored[:top_n] if _ > 0]
    return result if result else [sessions[0]]


def _check_code_validity(agent_path: Path) -> tuple[bool, str | None]:
    """Check if an agent file compiles and has a valid execute() function.

    Returns (valid, error_message).
    """
    source = agent_path.read_text(encoding="utf-8")
    try:
        compile(source, str(agent_path), "exec")
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"

    # Check for execute function by loading the module
    try:
        spec = importlib.util.spec_from_file_location("_critic_check", agent_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:  # noqa: BLE001 — generated agent code can raise anything on import
        return False, f"Import error: {e}"

    if not hasattr(module, "execute"):
        return False, "Missing execute() function"

    if not asyncio.iscoroutinefunction(module.execute):
        return False, "execute() is not async"

    return True, None


def _fix_common_llm_mistakes(code: str) -> str:
    """Fix common LLM mistakes in generated agent code."""
    code = code.replace(
        "llm_client.models.generate_content_async(",
        "llm_client.aio.models.generate_content(",
    )
    code = code.replace(
        "await llm_client.generate_content_async(",
        "await llm_client.aio.models.generate_content(",
    )
    # Ensure types import exists when GenerateContentConfig is used
    if (
        "types.GenerateContentConfig" in code
        and "from google.genai import types" not in code
    ):
        # Insert import after the docstring
        lines = code.split("\n")
        insert_idx = 0
        in_docstring = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(('"""', "'''")):
                if (
                    in_docstring
                    or stripped.count('"""') >= 2
                    or stripped.count("'''") >= 2
                ):
                    insert_idx = i + 1
                    break
                in_docstring = True
            elif not in_docstring and i > 0:
                insert_idx = i
                break
        lines.insert(insert_idx, "\nfrom google.genai import types\n")
        code = "\n".join(lines)

    # Ensure thinking budget cap is set (prevents truncation from runaway thinking)
    if "GenerateContentConfig" in code and "ThinkingConfig" not in code:
        code = code.replace(
            "max_output_tokens=65536)",
            "max_output_tokens=65536, thinking_config=types.ThinkingConfig(thinking_budget=2048))",
        )

    # Scrub harmful prompt patterns from generated agent code
    code = _scrub_harmful_prompt_patterns(code)

    return code


# Patterns that cause agents to waste turns asking about cut-off messages
# or micro-chunking their responses
_HARMFUL_PROMPT_PATTERNS = [
    re.compile(
        r"^.*(?:cut.?off|incomplete).*(?:message|thought|sentence).*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^.*(?:finish|complete)\s+(?:their|your)\s+(?:thought|sentence).*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^.*(?:does this|does that).*(?:make sense|sound right)\??.*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(r"^.*(?:shall I|should I)\s+continue.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"^.*ask\s+for\s+confirmation\s+before\s+proceed.*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    # Micro-chunking patterns (user_4 cafe agents)
    re.compile(r"^.*bite.?sized.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^.*one\s+concept\s+at\s+a\s+time.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"^.*(?:ask|end\s+(?:by|with))\s+(?:for\s+)?confirmation.*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^.*(?:gently|softly)\s+(?:prompt|nudge|ask).*(?:finish|complete|continue).*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^.*(?:incomplete|accidental).*(?:send|submission).*$",
        re.IGNORECASE | re.MULTILINE,
    ),
]


def _scrub_harmful_prompt_patterns(code: str) -> str:
    """Remove lines from prompt strings that cause harmful agent behavior.

    Scans ENRICHED_PROMPT and STEPS prompt strings for patterns like
    'if message is cut off' or 'ask for confirmation before proceeding'
    and removes matching lines.
    """
    for pattern in _HARMFUL_PROMPT_PATTERNS:
        code = pattern.sub("", code)
    # Clean up double blank lines left by removal
    while "\n\n\n" in code:
        code = code.replace("\n\n\n", "\n\n")
    return code


async def _critic_pass(
    user_id: str,
    user_dir: Path,
    task_patterns: list[Pattern],
    triggers: dict[str, dict],
    user_style_text: str,
    client: genai.Client,
    model: str,
) -> dict:
    """Run critic/revision pass on generated agents and triggers.

    For each agent:
    1. Validate code compiles and has async execute()
    2. Find a matching session from history as test case
    3. Run the agent on the test message
    4. Compare output against gold reference via critic LLM
    5. Rewrite agent/trigger if quality is insufficient

    Args:
        user_id: The user this swarm belongs to.
        user_dir: Path to the user's swarm directory.
        task_patterns: Task patterns that became agents.
        triggers: Trigger dict (mutated in-place if triggers revised).
        user_style_text: Formatted user style for prompts.
        client: Google Cloud genai client.
        model: Model for critic evaluation.

    Returns:
        Summary dict with revision counts and per-agent details.
    """
    # Load conversation history
    history_dir = user_dir.parent.parent / "history" / user_id
    if not history_dir.exists():
        return {
            "agents_revised": 0,
            "triggers_revised": 0,
            "skipped": True,
            "reason": "no history directory",
        }

    sessions = []
    for f in sorted(history_dir.glob("session_*.json")):
        try:
            sessions.append(json.loads(f.read_text()))
        except (json.JSONDecodeError, OSError):
            continue

    if not sessions:
        return {
            "agents_revised": 0,
            "triggers_revised": 0,
            "skipped": True,
            "reason": "no sessions found",
        }

    agents_dir = user_dir / "agents"
    agents_revised = 0
    triggers_revised = 0
    details = []

    for pidx, pattern in enumerate(task_patterns, 1):
        agent_name = pattern.pattern_name
        agent_path = agents_dir / f"{agent_name}.py"
        print(f"    Critic [{pidx}/{len(task_patterns)}] {agent_name}...", flush=True)
        if not agent_path.exists():
            details.append({"agent": agent_name, "status": "missing_file"})
            continue

        # Phase C: Code validity
        valid, error = _check_code_validity(agent_path)
        agent_code = agent_path.read_text(encoding="utf-8")

        # Phase B: Find test sessions and build per-session test data
        best_sessions = _find_best_sessions(sessions, pattern, top_n=3)

        test_scenarios = []  # list of (test_message, gold_response)
        for bs_idx, bs in enumerate(best_sessions, 1):
            bs_turns = bs.get("turns", [])
            t_msg = bs_turns[0]["content"] if bs_turns else "Hello"
            # Gold reference: first assistant turn from this session
            g_ref = ""
            for t in bs_turns:
                if t.get("role") == "assistant":
                    g_ref = f"--- Reference {bs_idx} ---\n{t['content']}"
                    break
            test_scenarios.append((t_msg, g_ref))

        # Combined gold for revision prompt (all references)
        all_gold_response = "\n\n".join(g for _, g in test_scenarios if g)

        # Parse user_style_text into dict for domain criteria (once per agent)
        user_style_dict = {}
        if user_style_text != "No specific style constraints.":
            for line in user_style_text.strip().split("\n"):
                line = line.strip().lstrip("- ")
                if ": " in line:
                    k, v = line.split(": ", 1)
                    user_style_dict[k.strip()] = v.strip()
        domain_criteria = _generate_domain_criteria(user_style_dict, pattern)
        pattern_prefs = json.dumps(pattern.user_preferences, indent=2)[:1500]
        trigger_desc = triggers.get(agent_name, {}).get("description", "")

        # Build styled test messages matching runtime behavior (Change 5)
        styled_scenarios = []
        for t_msg, g_ref in test_scenarios:
            styled_msg = t_msg
            if user_style_text and user_style_text != "No specific style constraints.":
                styled_msg = (
                    f"[STYLE INSTRUCTIONS — follow these for your response format:\n"
                    f"{user_style_text}]\n\n"
                    f"{t_msg}"
                )
            styled_scenarios.append((t_msg, styled_msg, g_ref))

        # Multi-round critic loop (up to 3 rounds)
        # Each round tests ALL scenarios — worst score must be >= 7 to pass
        max_rounds = 3
        prev_worst_score = -1
        final_detail = None

        for critic_round in range(max_rounds):
            # ── Run agent against ALL test scenarios ──────────────
            worst_score = 11  # higher than max so first result always wins
            worst_issues = []
            all_pass = True
            any_truncation_warning = ""
            round_trigger_pass = True
            round_revised_trigger = None

            for sc_idx, (raw_msg, styled_msg, gold_ref) in enumerate(styled_scenarios):
                # Run the agent (with retry on truncation)
                if not valid:
                    agent_output = f"[CODE ERROR: {error}]"
                else:
                    for exec_attempt in range(2):
                        try:
                            spec = importlib.util.spec_from_file_location(
                                f"_critic_{agent_name}_r{critic_round}_s{sc_idx}_a{exec_attempt}",
                                agent_path,
                            )
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            agent_output = await module.execute(styled_msg, client)
                            if agent_output is None:
                                agent_output = "[EMPTY RESPONSE: agent returned None]"
                        except Exception as e:  # noqa: BLE001 — generated agent code can raise anything
                            agent_output = f"[RUNTIME ERROR: {e}]"
                            break

                        # Check if output looks truncated
                        if agent_output and not agent_output.startswith("["):
                            stripped_check = agent_output.rstrip()
                            if (
                                stripped_check
                                and stripped_check[-1] not in ".!?\"')]:}\n*`"
                                and exec_attempt == 0
                            ):
                                print(
                                    f"      Truncation detected (scenario {sc_idx + 1}), retrying after 5s...",
                                    flush=True,
                                )
                                await asyncio.sleep(5)
                                continue  # retry
                        break  # not truncated or second attempt — stop

                # Log output size for diagnostics
                if agent_output and not agent_output.startswith("["):
                    print(
                        f"      Scenario {sc_idx + 1}/{len(styled_scenarios)}: {len(agent_output)} chars",
                        flush=True,
                    )

                # Truncation detection
                truncation_warning = ""
                if agent_output and not agent_output.startswith("["):
                    stripped = agent_output.rstrip()
                    if stripped and stripped[-1] not in ".!?\"')]:}\n*`":
                        truncation_warning = (
                            "\n\n## TRUNCATION FIX REQUIRED\n"
                            "The agent output was truncated (cut off mid-sentence). "
                            "Fixes needed: reduce ENRICHED_PROMPT to under 150 words, "
                            "add max_output_tokens=65536 with thinking_config=types.ThinkingConfig(thinking_budget=2048), "
                            "use at most 3 steps for dynamic agents."
                        )
                        any_truncation_warning = truncation_warning

                # ── Evaluate this scenario ──────────────────────────
                _CLIP_LIMIT = 12000
                if len(agent_output) > _CLIP_LIMIT:
                    clipped_output = (
                        agent_output[:_CLIP_LIMIT]
                        + "\n\n[... OUTPUT CLIPPED FOR EVALUATION — "
                        + f"full response is {len(agent_output)} chars and ends properly. "
                        + "Do NOT score this as truncation.]"
                    )
                else:
                    clipped_output = agent_output

                evaluate_prompt = _CRITIC_EVALUATE_PROMPT.format(
                    test_message=raw_msg[:2000],
                    agent_output=clipped_output,
                    gold_response=gold_ref[:6000],
                    user_style=user_style_text,
                    pattern_preferences=pattern_prefs,
                    domain_criteria=domain_criteria,
                    agent_name=agent_name,
                    trigger_description=trigger_desc,
                    truncation_warning=truncation_warning,
                )

                try:
                    from analyzer.llm_util import generate_with_fallback

                    response = await generate_with_fallback(
                        client=client,
                        model=model,
                        contents=evaluate_prompt,
                        config=genai.types.GenerateContentConfig(
                            temperature=0.1,
                            max_output_tokens=2048,
                        ),
                    )

                    verdict = _extract_json(response.text)
                    if isinstance(verdict, list):
                        verdict = (
                            verdict[0]
                            if verdict and isinstance(verdict[0], dict)
                            else {}
                        )
                    if not isinstance(verdict, dict):
                        verdict = {}
                except Exception as e:  # noqa: BLE001 — best-effort eval parse; neutral score on failure
                    # Evaluation call failed — default to neutral score (5) to
                    # trigger revision without catastrophically auto-failing
                    print(
                        f"      Scenario {sc_idx + 1} eval parse error: {e}", flush=True
                    )
                    verdict = {
                        "agent_pass": False,
                        "agent_score": 5,
                        "agent_issues": [
                            f"Evaluation JSON parse failed: {e} — defaulting to score 5"
                        ],
                        "trigger_pass": True,
                    }

                sc_score = verdict.get("agent_score", 0)
                sc_pass = verdict.get("agent_pass", True)
                sc_issues = verdict.get("agent_issues", [])

                # Enforce fabrication hard-ceiling: 2+ factual contradictions
                # caps score at 4 and forces revision
                factual_contradictions = verdict.get("factual_contradictions", 0)
                if factual_contradictions >= 2:
                    sc_pass = False
                    sc_score = min(sc_score, 4)
                    sc_issues = sc_issues + [
                        f"Fabrication ceiling: {factual_contradictions} factual contradictions detected"
                    ]

                if not sc_pass or sc_score < 7:
                    all_pass = False
                if sc_score < worst_score:
                    worst_score = sc_score
                    worst_issues = sc_issues

                # Collect trigger feedback from first scenario only
                if sc_idx == 0:
                    round_trigger_pass = verdict.get("trigger_pass", True)
                    round_revised_trigger = verdict.get("revised_trigger_description")

            # ── All scenarios evaluated — make decision ──────────────
            detail = {
                "agent": agent_name,
                "score": worst_score if worst_score <= 10 else 0,
                "agent_pass": all_pass,
                "trigger_pass": round_trigger_pass,
                "issues": worst_issues,
                "rounds": critic_round + 1,
                "scenarios_tested": len(styled_scenarios),
            }

            # Apply trigger revision (only on first round)
            if (
                critic_round == 0
                and not round_trigger_pass
                and round_revised_trigger
                and agent_name in triggers
            ):
                triggers[agent_name]["description"] = round_revised_trigger
                triggers_revised += 1
                detail["trigger_revised"] = True

            # If ALL scenarios pass (worst score >= 7), accept and stop
            if all_pass and worst_score >= 7:
                detail["status"] = "passed"
                final_detail = detail
                print(
                    f"      Round {critic_round + 1}: worst_score={worst_score} (all {len(styled_scenarios)} scenarios) ✓",
                    flush=True,
                )
                break

            # Score didn't improve from previous round — stop
            if worst_score <= prev_worst_score and critic_round > 0:
                detail["status"] = "no_improvement"
                final_detail = detail
                print(
                    f"      Round {critic_round + 1}: worst_score={worst_score} (no improvement)",
                    flush=True,
                )
                break

            prev_worst_score = worst_score
            print(
                f"      Round {critic_round + 1}: worst_score={worst_score} — revising...",
                flush=True,
            )

            # ── Revise using worst-case issues ─────────────────
            issues_text = "\n".join(f"- {issue}" for issue in worst_issues)
            if any_truncation_warning:
                issues_text += "\n- TRUNCATION: output was cut off mid-sentence"

            revise_prompt = _CRITIC_REVISE_PROMPT.format(
                issues=issues_text,
                agent_code=agent_code[:4000],
                user_style=user_style_text,
                pattern_preferences=pattern_prefs,
                test_message=styled_scenarios[0][0][:2000],
                gold_response=all_gold_response[:6000],
                truncation_warning=any_truncation_warning,
            )

            try:
                revise_response = await generate_with_fallback(
                    client=client,
                    model=model,
                    contents=revise_prompt,
                    config=genai.types.GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=4096,
                    ),
                )
                revised_code = revise_response.text.strip()
            except Exception as e:  # noqa: BLE001 — best-effort LLM revision call
                detail["status"] = "revision_call_failed"
                detail["error"] = str(e)
                final_detail = detail
                break

            revised_code = _fix_common_llm_mistakes(revised_code)

            if revised_code.startswith("```"):
                lines = revised_code.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                revised_code = "\n".join(lines)

            try:
                compile(revised_code, str(agent_path), "exec")
                agent_path.write_text(revised_code, encoding="utf-8")
                if (
                    any_truncation_warning
                    and len(revised_code) >= len(agent_code) * 0.9
                ):
                    detail["truncation_not_reduced"] = True
                agent_code = revised_code
                valid = True
                agents_revised += 1
                detail["status"] = "revised"
                final_detail = detail
            except SyntaxError:
                detail["status"] = "revision_failed_syntax"
                final_detail = detail
                break

        if final_detail is not None:
            details.append(final_detail)
        elif not details or details[-1].get("agent") != agent_name:
            details.append({"agent": agent_name, "status": "unknown"})

    return {
        "agents_revised": agents_revised,
        "triggers_revised": triggers_revised,
        "total_agents": len(task_patterns),
        "details": details,
    }


async def _compute_agent_embeddings(
    triggers: dict,
    patterns_by_name: dict,
    client: genai.Client,
) -> dict:
    """Compute scope embeddings for all agents using text-embedding-005.

    For each agent, builds a scope text from description + trigger_signals +
    typical_flow, then batch-embeds all agents in one API call.
    Stores the 768-dim vector in each trigger config as 'scope_embedding'.
    """
    scope_texts = {}
    agent_names = []

    for agent_name, trigger_config in triggers.items():
        if agent_name == "_config":
            continue  # skip per-user config entry
        pattern = patterns_by_name.get(agent_name)
        description = trigger_config.get("description", "")
        parts = [description]
        if pattern:
            if pattern.trigger_signals:
                parts.append("Keywords: " + ", ".join(pattern.trigger_signals))
            if pattern.typical_flow:
                parts.append("Typical tasks: " + "; ".join(pattern.typical_flow[:3]))
        scope_texts[agent_name] = " | ".join(parts)
        agent_names.append(agent_name)

    if not agent_names:
        return triggers

    texts_list = [scope_texts[name] for name in agent_names]
    try:
        response = await client.aio.models.embed_content(
            model=cfg.EMBED_MODEL,
            contents=texts_list,
        )
        if len(response.embeddings) == len(agent_names):
            for i, name in enumerate(agent_names):
                triggers[name]["scope_embedding"] = [
                    float(v) for v in response.embeddings[i].values
                ]
            print(f"  Embedded {len(agent_names)} agent scope texts (768-dim)")
        else:
            print(
                f"  Warning: batch embedding returned {len(response.embeddings)} "
                f"results for {len(agent_names)} agents, falling back to individual calls"
            )
            for i, name in enumerate(agent_names):
                try:
                    single_resp = await client.aio.models.embed_content(
                        model=cfg.EMBED_MODEL,
                        contents=texts_list[i],
                    )
                    if single_resp.embeddings:
                        triggers[name]["scope_embedding"] = [
                            float(v) for v in single_resp.embeddings[0].values
                        ]
                except Exception as e2:  # noqa: BLE001 — best-effort per-agent embedding
                    print(f"    Warning: embedding failed for {name}: {e2}")
    except Exception as e:  # noqa: BLE001 — best-effort batch embedding
        print(f"  Warning: embedding computation failed: {e}")

    return triggers


_AGENT_SCORE_PROMPT = """\
Score this mini-agent on 5 dimensions (1-5 each).

## User Persona
{user_persona}

## Agent Under Evaluation
- Name: {agent_name}
- Description: {agent_description}
- Frequency: {frequency} sessions (out of 50)
- Complexity: {complexity}
- Critic score: {critic_score}/10 (status: {critic_status})
- Critic issues: {critic_issues}
- Trigger domain: {trigger_domain}
- Trigger task_type: {trigger_task_type}

## Other Agents in the Swarm (for distinctiveness comparison)
{other_agents_summary}

## Scoring Rubric
1. **value** (1-5): How useful for this user's recurring needs?
   5 = frequent, complex task; 3 = moderate; 1 = rare/trivial
2. **distinctiveness** (1-5): How different from the other agents listed above?
   5 = unique domain; 3 = some overlap; 1 = largely redundant
3. **trigger_clarity** (1-5): How unambiguous are the trigger signals?
   5 = easy to distinguish; 3 = moderate overlap; 1 = vague/confusing
4. **quality** (1-5): Based on critic results?
   5 = passed first round (score>=7); 3 = needed revisions; 1 = failed
5. **frequency** (1-5): How strong is the frequency evidence?
   5 = 8+ sessions; 3 = 4-6 sessions; 1 = 2-3 sessions

Return ONLY: {{"value": N, "distinctiveness": N, "trigger_clarity": N, "quality": N, "frequency": N}}"""


async def _score_single_agent(
    agent_name: str,
    pattern: "Pattern",
    trigger: dict,
    critic_info: dict,
    other_agents_summary: str,
    user_persona: str,
    client: genai.Client,
    model: str,
) -> dict:
    """Score one agent on 5 dimensions via a single LLM call.

    Retries once on empty/None response before raising.
    """
    from analyzer.llm_util import generate_with_fallback

    rules = trigger.get("rules", {})
    prompt = _AGENT_SCORE_PROMPT.format(
        user_persona=user_persona,
        agent_name=agent_name,
        agent_description=trigger.get("description", pattern.description),
        frequency=pattern.frequency,
        complexity=pattern.complexity,
        critic_score=critic_info.get("score", "N/A"),
        critic_status=critic_info.get("status", "not_evaluated"),
        critic_issues=", ".join(critic_info.get("issues", [])) or "none",
        trigger_domain=rules.get("domain", "N/A"),
        trigger_task_type=rules.get("task_type", "N/A"),
        other_agents_summary=other_agents_summary,
    )

    response = await generate_with_fallback(
        client=client,
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=1024,
        ),
    )
    scores = _extract_json(response.text)
    # Clamp all scores to 1-5
    for key in ("value", "distinctiveness", "trigger_clarity", "quality", "frequency"):
        scores[key] = max(1, min(5, int(scores.get(key, 1))))
    return scores


_VETO_PROMPT = """\
You are reviewing a set of scored mini-agents for redundancy and overlap.

## User Persona
{user_persona}

## Scored Agents
{agents_table}

## Veto Criteria (veto if ANY apply)
- Agent is essentially redundant with a higher-scoring agent
- Agent handles something a general-purpose assistant does equally well
- Agent failed critic with score 0-2 AND was not successfully revised
- Agent's triggers overlap so heavily with another agent that runtime
  disambiguation would be unreliable

Which agents should be VETOED? Return a JSON object:
{{"vetoed": [{{"agent_name": "name", "reason": "one sentence"}}], "rationale": "summary"}}

If no agents should be vetoed, return: {{"vetoed": [], "rationale": "all agents are distinct"}}"""


async def _rank_and_select_agents(
    user_id: str,
    user_dir: Path,
    task_patterns: list[Pattern],
    triggers: dict[str, dict],
    manifest: dict,
    critic_summary: dict | None,
    user_persona: str,
    user_style_text: str,
    client: genai.Client,
    model: str,
    min_quality_score: int = MIN_QUALITY_SCORE,
) -> dict:
    """Rank agents via per-agent LLM scoring + programmatic ranking.

    Each agent is scored individually on 5 dimensions (tiny JSON response),
    then weighted totals are computed in Python. A separate veto pass
    detects redundant/overlapping agents. Falls back to frequency-based
    filtering on LLM failure.
    """
    from analyzer.llm_util import generate_with_fallback

    agents_dir = user_dir / "agents"
    agent_names = [p.pattern_name for p in task_patterns]

    # Build critic lookup
    critic_details = {}
    if critic_summary:
        for d in critic_summary.get("details", []):
            critic_details[d["agent"]] = d

    # Build compact summary of all agents (for distinctiveness scoring)
    agent_summaries = []
    for p in task_patterns:
        t = triggers.get(p.pattern_name, {})
        agent_summaries.append(
            f"- {p.pattern_name}: {t.get('description', p.description)[:100]}"
        )

    # ── Step 1: Score each agent individually (parallel, limit=2 to avoid rate limits) ──
    sem = asyncio.Semaphore(2)
    agent_scores: dict[str, dict] = {}

    async def score_one(pattern: Pattern) -> tuple[str, dict | None]:
        async with sem:
            # Build "other agents" list excluding this one
            others = "\n".join(
                s
                for s in agent_summaries
                if not s.startswith(f"- {pattern.pattern_name}:")
            )
            try:
                scores = await _score_single_agent(
                    agent_name=pattern.pattern_name,
                    pattern=pattern,
                    trigger=triggers.get(pattern.pattern_name, {}),
                    critic_info=critic_details.get(pattern.pattern_name, {}),
                    other_agents_summary=others,
                    user_persona=user_persona,
                    client=client,
                    model=model,
                )
                return (pattern.pattern_name, scores)
            except Exception as e:  # noqa: BLE001 — best-effort per-agent LLM scoring
                print(f"    Warning: scoring failed for {pattern.pattern_name}: {e}")
                return (pattern.pattern_name, None)

    score_results = await asyncio.gather(*[score_one(p) for p in task_patterns])

    failed_count = 0
    for name, scores in score_results:
        if scores:
            agent_scores[name] = scores
        else:
            failed_count += 1

    if failed_count == len(task_patterns):
        print("    Warning: all agent scoring failed, falling back to frequency-only")
        return _fallback_frequency_ranking(
            user_dir, task_patterns, triggers, manifest, min_quality_score
        )

    # ── Step 2: Compute weighted totals in Python ─────────────────
    rankings = []
    for pattern in task_patterns:
        name = pattern.pattern_name
        scores = agent_scores.get(name)
        if not scores:
            # Use conservative defaults for failed scoring
            scores = {
                "value": 2,
                "distinctiveness": 2,
                "trigger_clarity": 2,
                "quality": 2,
                "frequency": 2,
            }
        weighted = (
            scores["value"] * 3
            + scores["distinctiveness"] * 2
            + scores["trigger_clarity"] * 2
            + scores["quality"] * 2
            + scores["frequency"] * 1
        )
        rankings.append(
            {
                "agent_name": name,
                "scores": scores,
                "weighted_total": weighted,
                "vetoed": False,
                "veto_reason": None,
                "rank": None,  # assigned after veto pass
            }
        )

    rankings.sort(key=lambda r: r["weighted_total"], reverse=True)

    # ── Step 3: Veto pass (single LLM call) ───────────────────────
    agents_table = "\n".join(
        f"- {r['agent_name']} (total={r['weighted_total']}/50, "
        f"value={r['scores']['value']}, distinct={r['scores']['distinctiveness']}, "
        f"trigger={r['scores']['trigger_clarity']})"
        for r in rankings
    )

    try:
        veto_prompt = _VETO_PROMPT.format(
            user_persona=user_persona,
            agents_table=agents_table,
        )
        veto_response = await generate_with_fallback(
            client=client,
            model=model,
            contents=veto_prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=8192,
            ),
        )
        veto_result = _extract_json(veto_response.text)
        vetoed_names = set()
        for v in veto_result.get("vetoed", []):
            vname = v.get("agent_name", "")
            vreason = v.get("reason", "")
            if vname in agent_scores:
                vetoed_names.add(vname)
                for r in rankings:
                    if r["agent_name"] == vname:
                        r["vetoed"] = True
                        r["veto_reason"] = vreason
    except Exception as e:  # noqa: BLE001 — best-effort LLM veto pass
        print(f"    Warning: veto pass failed ({e}), skipping veto")
        veto_result = {"vetoed": [], "rationale": "veto pass failed"}

    # ── Step 4: Apply threshold + assign ranks ────────────────────
    selected = []
    rank = 1
    for r in rankings:
        if r["vetoed"]:
            continue
        if r["weighted_total"] >= min_quality_score:
            r["rank"] = rank
            selected.append(r["agent_name"])
            rank += 1

    if not selected:
        print(
            "    Warning: no agents above threshold after scoring, falling back to frequency-only"
        )
        return _fallback_frequency_ranking(
            user_dir, task_patterns, triggers, manifest, min_quality_score
        )

    # ── Step 5: Remove dropped agents ─────────────────────────────
    selected_set = set(selected)
    all_dropped = [n for n in agent_names if n not in selected_set]

    for name in all_dropped:
        agent_file = agents_dir / f"{name}.py"
        if agent_file.exists():
            agent_file.unlink()
        triggers.pop(name, None)

    manifest["agents"] = [a for a in manifest["agents"] if a["name"] in selected_set]
    manifest["agent_count"] = len(manifest["agents"])

    return {
        "selected": selected,
        "dropped": all_dropped,
        "rankings": rankings,
        "rationale": veto_result.get("rationale", ""),
        "min_quality_score": min_quality_score,
        "total_candidates": len(task_patterns),
    }


def _fallback_frequency_ranking(
    user_dir: Path,
    task_patterns: list[Pattern],
    triggers: dict[str, dict],
    manifest: dict,
    min_quality_score: int,
) -> dict:
    """Fallback: frequency + critic score filtering when LLM ranking fails.

    Uses frequency >= 5 (strong evidence) as primary filter. Patterns with
    frequency 3-4 are kept only if the critic scored them >= 7/10. This is
    stricter than the previous frequency >= 4 threshold to avoid keeping
    low-quality agents when LLM ranking is unavailable.
    """
    agents_dir = user_dir / "agents"
    sorted_patterns = sorted(task_patterns, key=lambda p: p.frequency, reverse=True)

    # Retrieve critic scores from manifest if available
    critic_details = manifest.get("critic_pass", {}).get("details", [])
    critic_scores = {}
    for d in critic_details:
        agent = d.get("agent", "")
        score = d.get("score")
        if agent and score is not None:
            try:
                critic_scores[agent] = float(score)
            except (ValueError, TypeError):
                pass

    # Keep patterns with strong frequency evidence OR moderate frequency + good critic score
    selected = []
    for p in sorted_patterns:
        critic_score = critic_scores.get(p.pattern_name, 0)
        if p.frequency >= 5 or (p.frequency >= 3 and critic_score >= 7):
            selected.append(p.pattern_name)

    # Always keep at least the top 3 by frequency
    if len(selected) < 3:
        selected = [p.pattern_name for p in sorted_patterns[:3]]
    dropped = [
        p.pattern_name for p in sorted_patterns if p.pattern_name not in set(selected)
    ]

    selected_set = set(selected)
    for name in dropped:
        agent_file = agents_dir / f"{name}.py"
        if agent_file.exists():
            agent_file.unlink()
        triggers.pop(name, None)

    manifest["agents"] = [a for a in manifest["agents"] if a["name"] in selected_set]
    manifest["agent_count"] = len(manifest["agents"])

    return {
        "selected": selected,
        "dropped": dropped,
        "rankings": [],
        "rationale": "Fallback: frequency-based filtering (LLM ranking failed)",
        "min_quality_score": min_quality_score,
        "total_candidates": len(task_patterns),
        "fallback": True,
    }


# ── Coverage validation ──────────────────────────────────────────────


def _validate_coverage(
    selected_agents: list[str],
    all_patterns: list["Pattern"],
    triggers: dict,
) -> list[dict]:
    """Check for coverage gaps after ranking cuts agents.

    For each dropped pattern, checks whether any surviving agent's rules
    would plausibly cover the dropped pattern's trigger signals. Returns
    a list of gap reports for patterns with no coverage.
    """
    selected_set = set(selected_agents)
    gaps = []

    for pattern in all_patterns:
        if pattern.pattern_name in selected_set:
            continue  # This pattern has its own agent

        # Check if any surviving agent's trigger_signals overlap
        covered = False
        for agent_name in selected_agents:
            if agent_name not in triggers:
                continue
            agent_desc = triggers[agent_name].get("description", "").lower()
            agent_signals = set()
            rules = triggers[agent_name].get("rules", {})
            for kw in rules.get("require_any_keyword", []):
                agent_signals.add(kw.lower())
            # Also check description words
            agent_signals.update(w.strip(".,;:()") for w in agent_desc.split())

            # Compute signal overlap
            dropped_signals = {s.lower() for s in pattern.trigger_signals}
            if not dropped_signals:
                covered = True
                break
            overlap = dropped_signals & agent_signals
            if len(overlap) / len(dropped_signals) > 0.3:
                covered = True
                break

        if not covered:
            gaps.append(
                {
                    "dropped_pattern": pattern.pattern_name,
                    "trigger_signals": pattern.trigger_signals,
                    "description": pattern.description,
                }
            )

    return gaps


async def _resolve_gaps(
    gaps: list[dict],
    selected_agents: list[str],
    triggers: dict,
    patterns_by_name: dict,
    client: genai.Client,
) -> dict:
    """Widen surviving agents to cover orphaned patterns.

    For each gap, finds the closest surviving agent by embedding similarity
    and merges the dropped pattern's domain into the agent's rules. Also
    removes any exclude_keywords that conflict with the absorbed signals.
    """
    import numpy as np

    for gap in gaps:
        dropped_name = gap["dropped_pattern"]
        dropped_signals = gap["trigger_signals"]

        # Find closest surviving agent by scope_embedding similarity
        best_agent = None
        best_sim = -1.0
        dropped_emb = None

        # Try to compute embedding for the dropped pattern's scope text
        dropped_pattern = patterns_by_name.get(dropped_name)
        if dropped_pattern:
            scope_text = gap["description"]
            if dropped_pattern.trigger_signals:
                scope_text += " | Keywords: " + ", ".join(
                    dropped_pattern.trigger_signals
                )
            try:
                embed_resp = await client.aio.models.embed_content(
                    model=cfg.EMBED_MODEL,
                    contents=scope_text[:2000],
                )
                dropped_emb = list(embed_resp.embeddings[0].values)
            except Exception as e:  # noqa: BLE001 — embedding is best-effort
                print(f"      Dropped-pattern embed skipped: {e}", flush=True)

        if dropped_emb:
            for agent_name in selected_agents:
                agent_emb = triggers.get(agent_name, {}).get("scope_embedding")
                if not agent_emb:
                    continue
                a = np.array(dropped_emb, dtype=np.float32)
                b = np.array(agent_emb, dtype=np.float32)
                sim = float(
                    np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
                )
                if sim > best_sim:
                    best_sim = sim
                    best_agent = agent_name
        else:
            # Fallback: pick the highest-frequency surviving agent
            best_agent = selected_agents[0] if selected_agents else None

        if not best_agent or best_agent not in triggers:
            continue

        rules = triggers[best_agent].get("rules", {})

        # Expand domain if the dropped pattern implies a different domain
        dropped_desc_lower = gap["description"].lower()
        if any(
            kw in dropped_desc_lower
            for kw in (
                "docker",
                "container",
                "deploy",
                "infrastructure",
                "terraform",
                "cloud run",
            )
        ):
            domains = rules.get("domain", [])
            if "devops_infrastructure" not in domains:
                rules["domain"] = domains + ["devops_infrastructure"]

        # Remove conflicting exclusions
        excl = rules.get("exclude_keywords", [])
        dropped_signal_set = {s.lower() for s in dropped_signals}
        excl = [e for e in excl if e.lower() not in dropped_signal_set]
        rules["exclude_keywords"] = excl

        triggers[best_agent]["rules"] = rules
        print(f"  Coverage: widened {best_agent} to absorb {dropped_name}")

    return triggers


def _expand_domains_for_user(triggers: dict, user_persona: str) -> dict:
    """Expand the broadest agent's domain to cover user's profile domains.

    For users whose profiles span multiple domains (e.g., Python + Google Cloud),
    ensure the highest-frequency agent accepts all relevant domains.
    """
    persona_lower = user_persona.lower()

    # Infer domains from persona
    user_domains = set()
    if any(
        kw in persona_lower
        for kw in (
            "python",
            "java",
            "code",
            "software",
            "engineer",
            "developer",
            "react",
            "frontend",
            "backend",
        )
    ):
        user_domains.add("software_engineering")
    if any(
        kw in persona_lower
        for kw in (
            "Google Cloud",
            "aws",
            "azure",
            "cloud",
            "docker",
            "kubernetes",
            "terraform",
            "devops",
            "infrastructure",
        )
    ):
        user_domains.add("devops_infrastructure")
    if any(
        kw in persona_lower
        for kw in (
            "data scientist",
            "data science",
            "ml",
            "machine learning",
            "analytics",
            "pandas",
            "sklearn",
        )
    ):
        user_domains.add("data_science_ml")

    if len(user_domains) <= 1:
        return triggers  # Single-domain user, no expansion needed

    # Find the broadest agent (highest frequency from description or first listed)
    broadest = None
    broadest_freq = -1
    for name, config in triggers.items():
        if name == "_config":
            continue
        # Use description length as proxy for breadth, or frequency if available
        rules = config.get("rules", {})
        current_domains = set(rules.get("domain", []))
        freq = len(current_domains)
        if freq >= broadest_freq:
            broadest_freq = freq
            broadest = name

    if broadest and broadest in triggers:
        rules = triggers[broadest].get("rules", {})
        current = set(rules.get("domain", []))
        merged = list(current | user_domains)
        if set(merged) != current:
            rules["domain"] = merged
            triggers[broadest]["rules"] = rules
            print(f"  Domain expansion: {broadest} now covers {merged}")

    return triggers


# ── Agent Merge Step ─────────────────────────────────────────────────


def _cosine_similarity_pure(vec_a: list[float], vec_b: list[float]) -> float:
    """Cosine similarity without numpy (used during generation)."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _jaccard(set_a: set, set_b: set) -> float:
    """Jaccard similarity between two sets."""
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def _agent_overlap_score(
    agent_i: str,
    agent_j: str,
    triggers: dict,
) -> float:
    """Compute overlap between two agents using three signals.

    - Embedding cosine similarity (weight 0.5)
    - Domain Jaccard overlap (weight 0.3)
    - Task-type Jaccard overlap (weight 0.2)
    """
    ti = triggers[agent_i]
    tj = triggers[agent_j]

    emb_sim = _cosine_similarity_pure(
        ti.get("scope_embedding", []),
        tj.get("scope_embedding", []),
    )
    dom_jaccard = _jaccard(
        set(ti.get("rules", {}).get("domain", [])),
        set(tj.get("rules", {}).get("domain", [])),
    )
    tt_jaccard = _jaccard(
        set(ti.get("rules", {}).get("task_type", [])),
        set(tj.get("rules", {}).get("task_type", [])),
    )
    return 0.5 * emb_sim + 0.3 * dom_jaccard + 0.2 * tt_jaccard


_MERGE_DECISION_PROMPT = """\
Two mini-agents have high trigger overlap (score: {overlap:.2f}).
Decide: MERGE them into one stronger agent, or KEEP both.

Agent A: {agent_a}
Description: {desc_a}
Domains: {domains_a}
Task types: {task_types_a}

Agent B: {agent_b}
Description: {desc_b}
Domains: {domains_b}
Task types: {task_types_b}

MERGE if:
- A user message that triggers one would ALSO reasonably trigger the other
  (i.e., the trigger system cannot reliably distinguish them)
- The agents cover the same real-world need from different angles
- Combining them would produce a single, more complete response

KEEP BOTH if:
- They handle genuinely different user goals despite sharing a domain
  (e.g., "write tests" vs "debug code" are both software engineering
  but serve different goals — KEEP)
- A user asking for one would NOT expect the other's response
- Merging would create an unfocused agent that tries to do too much

IMPORTANT: Sharing a domain (e.g., both are marketing, both are
software engineering) is NOT sufficient reason to merge. The question
is whether a TRIGGER SYSTEM can reliably tell them apart at runtime.

Reply ONLY with a JSON object:
{{"decision": "merge" or "keep", "reason": "one-sentence explanation",
  "merged_name": "snake_case_name" (if merge), \
"merged_description": "one-sentence scope" (if merge)}}"""


_MERGE_CODE_PROMPT = """\
You are merging two specialized mini-agents into a single, stronger agent.
The merged agent must handle the UNION of both scopes.

Agent A ({agent_a}):
```python
{code_a}
```

Agent B ({agent_b}):
```python
{code_b}
```

Merged agent name: {merged_name}
Merged scope: {merged_description}
User ID: {user_id}
User style:
{user_style_text}

Generate a single Python module for the merged agent. Follow the SAME
structure as the originals (AGENT_META dict, ENRICHED_PROMPT, async execute).
The merged agent should cover both scopes in its ENRICHED_PROMPT.
Keep complexity "static" unless one of the originals was "dynamic".

Output ONLY valid Python code, no markdown fences."""


async def _merge_overlapping_agents(
    task_patterns: list[Pattern],
    triggers: dict,
    agents_dir: Path,
    manifest: dict,
    user_style_text: str,
    user_id: str,
    client: genai.Client,
    model: str,
) -> dict:
    """Find and merge agent pairs with high trigger overlap.

    For each pair above MERGE_OVERLAP_THRESHOLD, asks an LLM whether
    they should merge or stay separate. Processes pairs in descending
    overlap order; once an agent is merged, skip remaining pairs involving it.

    Returns a summary dict for the manifest.
    """
    from analyzer.llm_util import generate_with_fallback

    agent_names = [
        name
        for name in triggers
        if name != "_config" and triggers[name].get("scope_embedding")
    ]

    # Score all pairs
    pairs = []
    for a, b in combinations(agent_names, 2):
        score = _agent_overlap_score(a, b, triggers)
        if score >= MERGE_OVERLAP_THRESHOLD:
            pairs.append((a, b, score))
    pairs.sort(key=lambda x: -x[2])

    if not pairs:
        print("  Merge pass: no pairs above threshold")
        return {"merges": [], "reviewed": 0, "kept": 0}

    print(
        f"  Merge pass: {len(pairs)} pair(s) above {MERGE_OVERLAP_THRESHOLD} threshold"
    )

    merged_away = set()  # agents absorbed into another
    merges = []
    kept = 0

    for agent_a, agent_b, overlap in pairs:
        if agent_a in merged_away or agent_b in merged_away:
            continue

        ti_a = triggers[agent_a]
        ti_b = triggers[agent_b]

        prompt = _MERGE_DECISION_PROMPT.format(
            overlap=overlap,
            agent_a=agent_a,
            desc_a=ti_a.get("description", ""),
            domains_a=ti_a.get("rules", {}).get("domain", []),
            task_types_a=ti_a.get("rules", {}).get("task_type", []),
            agent_b=agent_b,
            desc_b=ti_b.get("description", ""),
            domains_b=ti_b.get("rules", {}).get("domain", []),
            task_types_b=ti_b.get("rules", {}).get("task_type", []),
        )

        response = await generate_with_fallback(
            client=client,
            model=model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=1024,
            ),
        )

        try:
            verdict = _extract_json(response.text)
        except (json.JSONDecodeError, TypeError, AttributeError):
            verdict = {"decision": "keep", "reason": "LLM response unparseable"}

        if isinstance(verdict, list):
            verdict = verdict[0] if verdict and isinstance(verdict[0], dict) else {}

        decision = verdict.get("decision", "keep").lower().strip()

        if decision == "merge":
            merged_name = verdict.get("merged_name", agent_a)
            merged_desc = verdict.get("merged_description", ti_a.get("description", ""))
            print(
                f"    MERGE {agent_a} + {agent_b} → {merged_name} "
                f"(overlap={overlap:.3f}, reason: {verdict.get('reason', '')})"
            )

            # Generate merged agent code
            code_a = (agents_dir / f"{agent_a}.py").read_text(encoding="utf-8")
            code_b = (agents_dir / f"{agent_b}.py").read_text(encoding="utf-8")

            code_prompt = _MERGE_CODE_PROMPT.format(
                agent_a=agent_a,
                code_a=code_a,
                agent_b=agent_b,
                code_b=code_b,
                merged_name=merged_name,
                merged_description=merged_desc,
                user_id=user_id,
                user_style_text=user_style_text,
            )

            code_response = await generate_with_fallback(
                client=client,
                model=model,
                contents=code_prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=4096,
                ),
            )

            if code_response.text is None:
                print(
                    f"    MERGE ABORTED {agent_a} + {agent_b}: "
                    f"code generation returned None"
                )
                kept += 1
                continue
            merged_code = code_response.text.strip()
            if merged_code.startswith("```"):
                lines = merged_code.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                merged_code = "\n".join(lines)

            # Fix common LLM mistakes
            merged_code = _fix_common_llm_mistakes(merged_code)

            # Write merged agent file
            merged_path = agents_dir / f"{merged_name}.py"
            merged_path.write_text(merged_code, encoding="utf-8")

            # Merge trigger rules (union of domains and task_types)
            rules_a = ti_a.get("rules", {})
            rules_b = ti_b.get("rules", {})
            merged_rules = {
                "domain": list(
                    set(rules_a.get("domain", [])) | set(rules_b.get("domain", []))
                ),
                "task_type": list(
                    set(rules_a.get("task_type", []))
                    | set(rules_b.get("task_type", []))
                ),
            }
            # Keep the broader (lower) min_specificity
            from analyzer.trigger_schema import SPECIFICITY_ORDER

            spec_a = SPECIFICITY_ORDER.get(rules_a.get("min_specificity", "generic"), 0)
            spec_b = SPECIFICITY_ORDER.get(rules_b.get("min_specificity", "generic"), 0)
            merged_rules["min_specificity"] = (
                rules_a.get("min_specificity", "generic")
                if spec_a <= spec_b
                else rules_b.get("min_specificity", "generic")
            )

            # Create new trigger entry for merged agent
            triggers[merged_name] = {
                "trigger_type": "attribute_match",
                "rules": merged_rules,
                "description": merged_desc,
                # scope_embedding will be recomputed after all merges
            }

            # Determine which original to keep the name of
            # If merged_name equals one of the originals, only delete the other
            to_delete = set()
            if merged_name != agent_a:
                to_delete.add(agent_a)
            if merged_name != agent_b:
                to_delete.add(agent_b)

            for name in to_delete:
                # Remove old agent file
                old_path = agents_dir / f"{name}.py"
                if old_path.exists():
                    old_path.unlink()
                # Remove old trigger
                triggers.pop(name, None)
                merged_away.add(name)

            # If merged_name is entirely new (not equal to either original),
            # also mark both originals as merged away
            if merged_name != agent_a:
                merged_away.add(agent_a)
            if merged_name != agent_b:
                merged_away.add(agent_b)

            # Update manifest agents list
            manifest["agents"] = [
                a for a in manifest["agents"] if a["name"] not in merged_away
            ]
            # Add merged agent entry if it's new
            if not any(a["name"] == merged_name for a in manifest["agents"]):
                # Determine complexity from originals
                orig_complexities = []
                for a_entry in [agent_a, agent_b]:
                    for m_agent in manifest.get("_all_agents_backup", []):
                        if m_agent.get("name") == a_entry:
                            orig_complexities.append(
                                m_agent.get("complexity", "static")
                            )
                complexity = "dynamic" if "dynamic" in orig_complexities else "static"
                manifest["agents"].append(
                    {
                        "name": merged_name,
                        "file": f"agents/{merged_name}.py",
                        "complexity": complexity,
                        "frequency": 0,  # merged — no single frequency
                        "trigger_type": "attribute_match",
                    }
                )

            manifest["agent_count"] = len(manifest["agents"])

            merges.append(
                {
                    "agent_a": agent_a,
                    "agent_b": agent_b,
                    "merged_name": merged_name,
                    "overlap": round(overlap, 3),
                    "reason": verdict.get("reason", ""),
                }
            )
        else:
            kept += 1
            print(
                f"    KEEP {agent_a} + {agent_b} "
                f"(overlap={overlap:.3f}, reason: {verdict.get('reason', '')})"
            )

    return {"merges": merges, "reviewed": len(pairs), "kept": kept}


# ── Validation Gate ──────────────────────────────────────────────────

_QUICK_JUDGE_PROMPT = """\
Score this mini-agent response on a 1-4 scale.

User message: {message}
Goal: {goal_definition}
Agent response:
{agent_output}

CRITICAL — FABRICATION CHECK: Before scoring, verify all technical claims.
If the response contains ANY fabricated API names, CLI flags, URLs, function
names, or configuration parameters that do not exist → automatic score = 1.
Mention "fabrication detected" in the reason.

Scoring:
4 = Excellent: directly addresses the goal, accurate, well-structured,
    tailored to user preferences. All technical claims are verifiable.
3 = Good: addresses the goal with minor gaps. All technical claims are
    accurate or appropriately caveated.
2 = Marginal: partially addresses, significant gaps, or generic response
1 = Poor: misses the goal, inaccurate, contains fabricated technical claims,
    or unhelpful

Reply ONLY with a JSON object: {{"score": <1-4>, "reason": "one sentence"}}"""


def _pick_validation_scenarios_from_cache(
    agent_name: str,
    triggers: dict,
    history_cache: list[tuple[dict, str, list[float] | None, dict]],
) -> tuple[list[dict], list[dict]]:
    """Pick similar + different-candidate scenarios from pre-computed cache.

    Returns:
        (sim_candidates, diff_candidates) — each has up to 6 items with
        a ``needs_llm_check`` flag. Both lists go through LLM verification
        before being used in validation.
    """
    from analyzer.trigger_schema import match_agent_rules_with_embedding

    if not history_cache:
        return [], []

    agent_trigger = triggers.get(agent_name)
    if not agent_trigger or not agent_trigger.get("scope_embedding"):
        return [], []

    agent_rules = agent_trigger.get("rules", {})
    agent_scope_emb = agent_trigger.get("scope_embedding")

    user_config = triggers.get("_config", {})
    sim_threshold = user_config.get("similarity_threshold")

    # Score each cached session against THIS agent
    scored: list[tuple[dict, str, float | None]] = []
    for sess, msg, emb, feat in history_cache:
        if emb is None:
            scored.append((sess, msg, None))
            continue

        match_kwargs = {}
        if sim_threshold is not None:
            match_kwargs["similarity_threshold"] = sim_threshold

        score = match_agent_rules_with_embedding(
            feat, agent_rules, emb, agent_scope_emb, **match_kwargs
        )
        scored.append((sess, msg, score))

    # Split into matching vs non-matching
    matching = [(s, m, sc) for s, m, sc in scored if sc is not None]
    non_matching = [(s, m, sc) for s, m, sc in scored if sc is None]

    # Top matching by score → "similar" candidates (up to 6 for LLM verification)
    matching.sort(key=lambda x: x[2], reverse=True)

    sim_candidates: list[dict] = []
    for sess, msg, sc in matching[:6]:
        # Extract gold reference (first assistant response) for goal generation
        gold_response = ""
        for turn in sess.get("turns", []):
            if turn.get("role") == "assistant" and turn.get("content", "").strip():
                gold_response = turn["content"].strip()[:500]
                break
        sim_candidates.append(
            {
                "message": msg,
                "category": "similar",
                "goal_definition": sess.get("intent", "Address the user's request"),
                "intent": sess.get("intent", ""),
                "follow_up_strategy": sess.get("follow_up_strategy", "clarify"),
                "max_turns": 3,
                "gold_response": gold_response,
                "source_session": sess.get("scenario_id", "unknown"),
                "needs_llm_check": True,  # all similar candidates get LLM verification
            }
        )

    # Build a pool of "different" candidates (up to 6 for LLM verification).
    # Non-matching sessions first, then lowest-scoring matching as fallback.
    import random

    non_matching_shuffled = list(non_matching)
    random.shuffle(non_matching_shuffled)

    diff_candidates: list[dict] = []
    for sess, msg, sc in non_matching_shuffled[:6]:
        diff_candidates.append(
            {
                "message": msg,
                "category": "different",
                "expected_action": "none",
                "source_session": sess.get("scenario_id", "unknown"),
                "needs_llm_check": False,  # non-matching → high confidence negative
            }
        )

    # Fallback: if not enough non-matching, add lowest-scoring matching.
    # These need LLM verification because they DID match this agent.
    if len(diff_candidates) < 6 and len(matching) > len(sim_candidates):
        # Reverse matching (lowest score first), skip those used as sim_candidates
        fallback_pool = list(reversed(matching[len(sim_candidates) :]))
        for sess, msg, sc in fallback_pool[: 6 - len(diff_candidates)]:
            diff_candidates.append(
                {
                    "message": msg,
                    "category": "different",
                    "expected_action": "none",
                    "source_session": sess.get("scenario_id", "unknown"),
                    "needs_llm_check": True,  # matched this agent → verify it's different
                }
            )

    return sim_candidates, diff_candidates


_SIM_VERIFY_PROMPT = """\
You are validating test scenarios for a specialized mini-agent.

Agent: {agent_name}
Agent description: {agent_description}
Agent domains: {agent_domains}
Agent task types: {agent_task_types}

A user message has been selected as a POSITIVE test case — it SHOULD
be handled by this agent. Verify whether this message is genuinely
within the agent's scope.

User message:
"{message}"

Reply ONLY with a JSON object:
{{"is_relevant": true/false, "reason": "one sentence"}}

Rules:
- "is_relevant": true means this message clearly falls within the agent's
  scope (matching domain AND task type — the agent should handle it).
- "is_relevant": false means this message is outside the agent's scope
  (different domain, different task type, or only superficially related).
- Be strict: the message must genuinely need this SPECIFIC agent's
  expertise, not just share vocabulary with it."""


async def _verify_similar_scenarios(
    agent_name: str,
    agent_trigger: dict,
    candidates: list[dict],
    client: genai.Client,
    model: str,
    needed: int = 3,
) -> list[dict]:
    """LLM-verify that 'similar' candidates are genuinely relevant tasks.

    Uses Gemini 3.1 Pro to confirm each candidate message actually falls
    within the agent's scope before using it for quality validation.

    Returns up to ``needed`` verified scenarios.
    """
    from analyzer.llm_util import generate_with_fallback

    verified: list[dict] = []

    for candidate in candidates:
        if len(verified) >= needed:
            break

        prompt = _SIM_VERIFY_PROMPT.format(
            agent_name=agent_name,
            agent_description=agent_trigger.get("description", ""),
            agent_domains=agent_trigger.get("rules", {}).get("domain", []),
            agent_task_types=agent_trigger.get("rules", {}).get("task_type", []),
            message=candidate["message"][:500],
        )

        try:
            response = await generate_with_fallback(
                client=client,
                model=model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1024,
                ),
            )
            result = _extract_json(response.text)
            if result.get("is_relevant", False):
                out = {k: v for k, v in candidate.items() if k != "needs_llm_check"}
                verified.append(out)
            # else: skip — LLM says this message isn't actually relevant
        except Exception as e:  # noqa: BLE001 — fail open: accept candidate on any error
            print(f"      Relevance check skipped: {e}", flush=True)
            # On error, accept the candidate (embedding match is decent signal)
            out = {k: v for k, v in candidate.items() if k != "needs_llm_check"}
            verified.append(out)

    return verified


_DIFF_VERIFY_PROMPT = """\
You are validating test scenarios for a specialized mini-agent.

Agent: {agent_name}
Agent description: {agent_description}
Agent domains: {agent_domains}
Agent task types: {agent_task_types}

A user message has been selected as a NEGATIVE test case — it should NOT
be handled by this agent. Verify whether this message is genuinely a
DIFFERENT task, or whether it is actually within the agent's scope.

User message:
"{message}"

Reply ONLY with a JSON object:
{{"is_different": true/false, "reason": "one sentence"}}

Rules:
- "is_different": true means this message is clearly outside the agent's
  scope (different domain, different task type, or unrelated intent).
- "is_different": false means this message could reasonably be handled by
  this agent (same domain + similar task, just a weaker match)."""


async def _verify_different_scenarios(
    agent_name: str,
    agent_trigger: dict,
    candidates: list[dict],
    client: genai.Client,
    model: str,
    needed: int = 3,
) -> list[dict]:
    """LLM-verify that 'different' candidates are genuinely different tasks.

    For candidates with needs_llm_check=False (scored None by trigger
    matching), accept them directly. For candidates with
    needs_llm_check=True (fallback from matched pool), ask an LLM to
    confirm they are genuinely different.

    Returns up to ``needed`` verified scenarios.
    """
    from analyzer.llm_util import generate_with_fallback

    verified: list[dict] = []

    for candidate in candidates:
        if len(verified) >= needed:
            break

        # Non-matching sessions are high-confidence negatives — accept directly
        if not candidate.get("needs_llm_check", False):
            # Strip internal flag before returning
            out = {k: v for k, v in candidate.items() if k != "needs_llm_check"}
            verified.append(out)
            continue

        # Fallback candidates need LLM verification
        prompt = _DIFF_VERIFY_PROMPT.format(
            agent_name=agent_name,
            agent_description=agent_trigger.get("description", ""),
            agent_domains=agent_trigger.get("rules", {}).get("domain", []),
            agent_task_types=agent_trigger.get("rules", {}).get("task_type", []),
            message=candidate["message"][:500],
        )

        try:
            response = await generate_with_fallback(
                client=client,
                model=model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1024,
                ),
            )
            result = _extract_json(response.text)
            if result.get("is_different", False):
                out = {k: v for k, v in candidate.items() if k != "needs_llm_check"}
                verified.append(out)
            # else: skip this candidate — LLM says it's actually similar
        except Exception as e:  # noqa: BLE001 — skip candidate rather than accept a bad negative
            print(f"      Candidate verification skipped: {e}", flush=True)
            continue

    return verified


async def _execute_agent_for_validation(
    agent_name: str,
    message: str,
    agents_dir: Path,
    client: genai.Client,
    user_style_text: str = "",
    history: list[dict] | None = None,
) -> str | None:
    """Execute a single agent against a message. Returns output or None.

    Retries once after a 5s delay if the output appears truncated
    (ends mid-word), which can happen under transient API conditions.
    If user_style_text is provided, injects style prefix matching runtime.
    Supports multi-turn via history parameter.
    """
    agent_path = agents_dir / f"{agent_name}.py"
    if not agent_path.exists():
        return None

    # Inject style to match runtime behavior
    styled_message = message
    if user_style_text and user_style_text != "No specific style constraints.":
        styled_message = (
            f"[STYLE INSTRUCTIONS — follow these for your response format:\n"
            f"{user_style_text}]\n\n"
            f"{message}"
        )

    for attempt in range(2):
        try:
            spec = importlib.util.spec_from_file_location(
                f"_val_{agent_name}_a{attempt}", agent_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Pass history if the agent supports it
            import inspect

            sig = inspect.signature(module.execute)
            if "history" in sig.parameters and history:
                output = await module.execute(styled_message, client, history=history)
            else:
                output = await module.execute(styled_message, client)

            if not output:
                return None
            # Retry on truncation
            stripped = output.rstrip()
            if stripped and stripped[-1] not in ".!?\"')]:}\n*`" and attempt == 0:
                await asyncio.sleep(5)
                continue
            return output
        except Exception as e:  # noqa: BLE001 — generated agent code can raise anything
            print(f"    Validation: {agent_name} execution error: {e}")
            return None
    return output  # return whatever we got after retries


async def _quick_judge(
    message: str,
    agent_output: str,
    goal_definition: str,
    client: genai.Client,
    model: str,
) -> float:
    """Score agent output quality on 1-4 scale."""
    from analyzer.llm_util import generate_with_fallback

    _QJ_CLIP = 12000
    if len(agent_output) > _QJ_CLIP:
        clipped = (
            agent_output[:_QJ_CLIP]
            + "\n\n[... OUTPUT CLIPPED — full response is "
            + f"{len(agent_output)} chars. Do NOT penalize for clipping.]"
        )
    else:
        clipped = agent_output
    prompt = _QUICK_JUDGE_PROMPT.format(
        message=message,
        goal_definition=goal_definition,
        agent_output=clipped,
    )

    response = await generate_with_fallback(
        client=client,
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=1.0,
            max_output_tokens=1024,
        ),
    )

    try:
        result = _extract_json(response.text)
        if isinstance(result, list):
            result = result[0] if result else {}
        score = float(result.get("score", 1))
        return max(1.0, min(4.0, score))
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
        return 1.0


async def _run_agent_validation(
    agent_name: str,
    scenarios: list[dict],
    agents_dir: Path,
    triggers: dict,
    client: genai.Client,
    model: str,
    user_style_text: str = "",
    persona: str = "",
    user_id: str = "",
) -> dict:
    """Run validation for one agent using the full multi-turn eval harness.

    For similar scenarios:
    - Runs a multi-turn conversation using the simulated user agent
    - Calls the agent's execute() directly (no ADK runner)
    - Judges quality using the same 3-dimension LLM judge as final eval
      (accuracy, helpfulness, personalization)
    - Trigger accuracy tracked separately

    For different scenarios:
    - Only runs trigger matching (false-positive detection)
    """
    from analyzer.trigger_matcher import match_message_to_agent
    from eval.harness import (
        build_style_hints,
        judge_conversation,
        run_eval_user_turn,
    )

    results = []
    similar_count = 0
    different_count = 0

    # Load user style for simulated user hints
    style_hints = ""
    if user_style_text and user_style_text != "No specific style constraints.":
        try:
            user_style_dict = json.loads(user_style_text)
            style_hints = build_style_hints(user_style_dict)
        except (json.JSONDecodeError, TypeError):
            pass

    # Load rubric for judge
    rubric_path = Path(__file__).parent.parent / "evaluation_rubric_augmented.md"
    rubric_text = ""
    if rubric_path.exists():
        rubric_text = rubric_path.read_text()

    for scenario in scenarios:
        message = scenario["message"]
        category = scenario["category"]

        # Run trigger matching
        matched_agent = await match_message_to_agent(message, triggers, client)

        if category == "similar":
            similar_count += 1
            trigger_correct = matched_agent == agent_name

            # ── Multi-turn conversation with agent ──────────────────
            intent = scenario.get("intent", scenario.get("goal_definition", ""))
            follow_up_strategy = scenario.get("follow_up_strategy", "clarify")
            goal_definition = scenario.get("goal_definition", "")
            max_turns = scenario.get("max_turns", 3)

            turns = []
            user_message = message
            goal_reached = False
            history = []

            for turn_num in range(1, max_turns + 1):
                # Execute agent
                output = await _execute_agent_for_validation(
                    agent_name,
                    user_message,
                    agents_dir,
                    client,
                    user_style_text=user_style_text,
                    history=history,
                )
                if not output:
                    output = "(no response)"

                turns.append({"role": "user", "content": user_message})
                turns.append({"role": "assistant", "content": output})
                history = list(turns)  # copy for next turn

                # Check if goal reached via simulated user
                if turn_num < max_turns:
                    next_message = await run_eval_user_turn(
                        client,
                        persona,
                        intent,
                        follow_up_strategy,
                        output,
                        turn_num + 1,
                        goal_definition=goal_definition,
                        style_hints=style_hints,
                    )
                    if next_message is None:
                        goal_reached = True
                        break
                    user_message = next_message

            # ── Judge the conversation ──────────────────────────────
            augmented_result = {
                "turns": turns,
                "turn_count": len(turns) // 2,
                "goal_reached": goal_reached,
            }

            # Build scenario_info matching judge_conversation format
            scenario_info = {
                "name": f"validation_{agent_name}_{scenario.get('source_session', 'unknown')}",
                "user_id": user_id,
                "persona": persona,
                "scenario": {
                    "intent": intent,
                },
            }

            judge_result = await judge_conversation(
                scenario_info=scenario_info,
                baseline_result=None,
                augmented_result=augmented_result,
                rubric_text=rubric_text,
                judge_client=client,
            )

            # Extract scores
            accuracy = 1.0
            helpfulness = 1.0
            personalization = 1.0
            if judge_result and "augmented" in judge_result:
                scores = judge_result["augmented"]
                accuracy = float(scores.get("accuracy", 1))
                helpfulness = float(scores.get("helpfulness", 1))
                personalization = float(scores.get("personalization", 1))

            # Quality = average of all 3 dimensions (same as final eval)
            quality_score = (accuracy + helpfulness + personalization) / 3.0

            results.append(
                {
                    "category": "similar",
                    "trigger_correct": trigger_correct,
                    "matched_agent": matched_agent,
                    "quality_score": round(quality_score, 2),
                    "accuracy": accuracy,
                    "helpfulness": helpfulness,
                    "personalization": personalization,
                    "goal_reached": goal_reached,
                    "turn_count": len(turns) // 2,
                }
            )

        elif category == "different":
            different_count += 1
            false_positive = matched_agent == agent_name
            results.append(
                {
                    "category": "different",
                    "false_positive": false_positive,
                    "matched_agent": matched_agent,
                }
            )

    similar_results = [r for r in results if r["category"] == "similar"]
    different_results = [r for r in results if r["category"] == "different"]

    similar_trigger_rate = sum(
        1 for r in similar_results if r.get("trigger_correct")
    ) / max(similar_count, 1)
    # Average quality only over scenarios where the agent produced output
    scored_results = [r for r in similar_results if r.get("quality_score", 0) > 0]
    similar_avg_quality = sum(r["quality_score"] for r in scored_results) / max(
        len(scored_results), 1
    )
    # Track accuracy separately for fabrication-based pruning
    similar_avg_accuracy = sum(r.get("accuracy", 1) for r in scored_results) / max(
        len(scored_results), 1
    )
    false_positive_count = sum(1 for r in different_results if r.get("false_positive"))
    # Flag if any scenario got accuracy=1 (fabrication detected)
    has_fabrication = any(r.get("accuracy", 4) <= 1 for r in similar_results)

    return {
        "agent_name": agent_name,
        "results": results,
        "similar_trigger_rate": similar_trigger_rate,
        "similar_avg_quality": round(similar_avg_quality, 2),
        "similar_avg_accuracy": round(similar_avg_accuracy, 2),
        "has_fabrication": has_fabrication,
        "false_positive_count": false_positive_count,
    }


async def _run_validation_gate(
    triggers: dict,
    manifest: dict,
    agents_dir: Path,
    user_id: str,
    client: genai.Client,
    model: str,
    user_style_text: str = "",
) -> dict:
    """Run validation gate on all surviving agents.

    Pre-computes embeddings and features for all history sessions once,
    then for each agent: select test scenarios from real history,
    run multi-turn conversations with simulated user + 3-dimension judge
    (same harness as final eval), prune agents that fail.
    """
    agent_names = [a["name"] for a in manifest["agents"]]

    if not agent_names:
        return {"validation_results": [], "removed": [], "surviving": 0}

    # Load user persona for simulated user agent
    profiles_path = Path(__file__).parent.parent / "user_profiles" / "profiles.json"
    persona = ""
    if profiles_path.exists():
        try:
            profiles = json.loads(profiles_path.read_text())
            for u in profiles.get("users", []):
                if u["user_id"] == user_id:
                    persona = u.get("persona", "")
                    break
        except (json.JSONDecodeError, OSError):
            pass

    print(
        f"  Validation gate: testing {len(agent_names)} agents "
        f"(6 scenarios each: 3 similar + 3 different, multi-turn eval)..."
    )

    # ── Pre-compute history embeddings + features once ────────────────
    from analyzer.trigger_matcher import embed_message, extract_features

    history_dir = Path(__file__).parent.parent / "history" / user_id
    sessions = []
    if history_dir.exists():
        for f in sorted(history_dir.glob("session_*.json")):
            try:
                sessions.append(json.loads(f.read_text()))
            except (json.JSONDecodeError, OSError):
                continue

    # Extract first user message from each session
    first_messages: list[tuple[dict, str]] = []
    for sess in sessions:
        for turn in sess.get("turns", []):
            if turn.get("role") == "user" and turn.get("content", "").strip():
                first_messages.append((sess, turn["content"].strip()))
                break

    # Pre-compute embeddings + features for all messages concurrently
    history_cache: list[tuple[dict, str, list[float] | None, dict]] = []
    if first_messages:
        embed_tasks = [embed_message(msg, client) for _, msg in first_messages]
        feature_tasks = [extract_features(msg, client) for _, msg in first_messages]
        all_results = await asyncio.gather(
            *embed_tasks, *feature_tasks, return_exceptions=True
        )
        n = len(first_messages)
        for i, (sess, msg) in enumerate(first_messages):
            emb = all_results[i]
            feat = all_results[n + i]
            history_cache.append(
                (
                    sess,
                    msg,
                    None if isinstance(emb, Exception) else emb,
                    {} if isinstance(feat, Exception) else feat,
                )
            )
        print(f"    Pre-computed {len(history_cache)} session embeddings + features")

    validation_results = []

    # Process agents with concurrency limit to avoid rate limits
    sem = asyncio.Semaphore(3)

    async def validate_one(agent_name: str) -> dict:
        async with sem:
            sim_candidates, diff_candidates = _pick_validation_scenarios_from_cache(
                agent_name, triggers, history_cache
            )
            if not sim_candidates and not diff_candidates:
                print(f"    {agent_name}: no valid scenarios from history, skipping")
                return {
                    "agent_name": agent_name,
                    "results": [],
                    "similar_trigger_rate": 1.0,
                    "similar_avg_quality": 3.0,
                    "false_positive_count": 0,
                    "skipped": True,
                }

            agent_trigger = triggers.get(agent_name, {})

            # LLM-verify both similar and different candidates
            similar = await _verify_similar_scenarios(
                agent_name,
                agent_trigger,
                sim_candidates,
                client,
                model,
                needed=3,
            )
            different = await _verify_different_scenarios(
                agent_name,
                agent_trigger,
                diff_candidates,
                client,
                model,
                needed=3,
            )

            scenarios = similar + different
            if not scenarios:
                print(f"    {agent_name}: no scenarios survived verification, skipping")
                return {
                    "agent_name": agent_name,
                    "results": [],
                    "similar_trigger_rate": 1.0,
                    "similar_avg_quality": 3.0,
                    "false_positive_count": 0,
                    "skipped": True,
                }

            return await _run_agent_validation(
                agent_name,
                scenarios,
                agents_dir,
                triggers,
                client,
                model,
                user_style_text=user_style_text,
                persona=persona,
                user_id=user_id,
            )

    tasks = [validate_one(name) for name in agent_names]
    validation_results = await asyncio.gather(*tasks)

    # Prune failing agents
    removed = []
    for vr in validation_results:
        agent = vr["agent_name"]
        if vr.get("skipped"):
            print(f"    {agent}: SKIPPED (no scenarios)")
            continue

        fail_reasons = []

        if vr["similar_avg_quality"] < VALIDATION_MIN_QUALITY:
            fail_reasons.append(
                f"low quality ({vr['similar_avg_quality']:.1f} < "
                f"{VALIDATION_MIN_QUALITY})"
            )

        if vr["similar_trigger_rate"] == 0:
            fail_reasons.append("never triggered on similar scenarios (0/3)")

        if vr["false_positive_count"] > VALIDATION_MAX_FALSE_POSITIVES:
            fail_reasons.append(
                f"high false positives ({vr['false_positive_count']}/3)"
            )

        if vr.get("has_fabrication"):
            fail_reasons.append(
                "fabrication detected (accuracy=1 in at least one scenario)"
            )

        if fail_reasons:
            agent_file = agents_dir / f"{agent}.py"
            if agent_file.exists():
                agent_file.unlink()
            triggers.pop(agent, None)
            manifest["agents"] = [a for a in manifest["agents"] if a["name"] != agent]
            removed.append({"agent": agent, "reasons": fail_reasons})
            print(f"    Validation REMOVED: {agent} — {'; '.join(fail_reasons)}")
        else:
            acc_str = f", acc={vr.get('similar_avg_accuracy', 'N/A')}"
            print(
                f"    Validation PASSED: {agent} "
                f"(quality={vr['similar_avg_quality']:.1f}{acc_str}, "
                f"trigger={vr['similar_trigger_rate']:.0%}, "
                f"FP={vr['false_positive_count']})"
            )

    manifest["agent_count"] = len(manifest["agents"])

    return {
        "validation_results": [
            {k: v for k, v in vr.items() if k != "results"} for vr in validation_results
        ],
        "removed": removed,
        "surviving": len(manifest["agents"]),
    }


async def generate_swarm(
    patterns: list[Pattern],
    user_id: str,
    output_dir: Path,
    client: genai.Client,
    model: str = cfg.ANALYSIS_MODEL,
    skip_critic: bool = False,
) -> dict:
    """Generate a complete swarm for a user.

    Creates:
        {output_dir}/{user_id}/manifest.json
        {output_dir}/{user_id}/triggers.json
        {output_dir}/{user_id}/user_style.json  (from behavioral patterns)
        {output_dir}/{user_id}/agents/{pattern_name}.py

    Args:
        patterns: Extracted patterns from pattern_extractor.
        user_id: The user this swarm belongs to.
        output_dir: Base swarms directory.
        client: Google Cloud genai client.
        model: Model for agent code generation.

    Returns:
        The manifest dict.
    """
    import shutil

    user_dir = output_dir / user_id
    agents_dir = user_dir / "agents"

    # Load user persona for ranking prompt
    profiles_path = Path(__file__).parent.parent / "user_profiles" / "profiles.json"
    user_persona = ""
    if profiles_path.exists():
        profiles_data = json.loads(profiles_path.read_text())
        for u in profiles_data.get("users", []):
            if u["user_id"] == user_id:
                user_persona = u.get("persona", "")
                break
    # Clean stale agents from previous runs (load_swarm globs all .py files)
    if agents_dir.exists():
        shutil.rmtree(agents_dir)
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Separate behavioral from task patterns
    task_patterns = [p for p in patterns if p.pattern_type == "task"]
    behavioral_patterns = [p for p in patterns if p.pattern_type == "behavioral"]

    # Tier 1: Hard safety cap — only for extreme cases
    if len(task_patterns) > HARD_CAP_AGENTS:
        task_patterns.sort(key=lambda p: p.frequency, reverse=True)
        dropped = task_patterns[HARD_CAP_AGENTS:]
        task_patterns = task_patterns[:HARD_CAP_AGENTS]
        print(
            f"  Hard cap: kept top {HARD_CAP_AGENTS}, "
            f"dropped {[p.pattern_name for p in dropped]}"
        )

    # Generate user style profile from behavioral patterns
    user_style = await _generate_user_style(
        behavioral_patterns, task_patterns, client, model
    )

    # Write raw user_style.json (for reference)
    style_path = user_dir / "user_style.json"
    style_path.write_text(json.dumps(user_style, indent=2, ensure_ascii=False))

    # Sanitize style for agent prompt injection (removes harmful patterns)
    user_style = _sanitize_user_style(user_style)

    # Format style as text for embedding in agent prompts
    if user_style:
        user_style_text = "\n".join(f"- {k}: {v}" for k, v in user_style.items())
    else:
        user_style_text = "No specific style constraints."

    triggers = {}
    manifest_agents = []
    patterns_by_name = {p.pattern_name: p for p in task_patterns}

    for idx, pattern in enumerate(task_patterns, 1):
        print(
            f"    [{idx}/{len(task_patterns)}] Generating {pattern.pattern_name}...",
            flush=True,
        )
        # Generate trigger
        trigger = _create_trigger(pattern)
        triggers[pattern.pattern_name] = trigger

        # Resolve complexity (may override dynamic -> static)
        resolved_complexity = _resolve_complexity(pattern, user_style)

        # Generate anti-pattern instructions
        anti_pattern_text = _generate_anti_pattern_instructions(user_style)

        # Generate agent code via LLM
        prompt = _AGENT_GEN_PROMPT.format(
            pattern_name=pattern.pattern_name,
            description=pattern.description,
            typical_flow=json.dumps(pattern.typical_flow),
            user_preferences=json.dumps(pattern.user_preferences),
            complexity=resolved_complexity,
            frequency=pattern.frequency,
            user_id=user_id,
            user_style=user_style_text,
            anti_patterns=anti_pattern_text,
        )

        from analyzer.llm_util import generate_with_fallback

        # Parallel generation: 2 candidates at different temperatures,
        # then pick the more grounded one
        async def _gen_candidate(temp: float, prompt=prompt):
            resp = await generate_with_fallback(
                client=client,
                model=model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=temp,
                    max_output_tokens=4096,
                ),
            )
            return resp.text.strip() if resp.text else ""

        cand_a, cand_b = await asyncio.gather(_gen_candidate(0.2), _gen_candidate(0.35))

        def _clean_agent_code(code: str) -> str:
            if code.startswith("```"):
                lines = code.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                code = "\n".join(lines)
            code = code.replace(
                "llm_client.models.generate_content_async(",
                "llm_client.aio.models.generate_content(",
            )
            code = code.replace(
                "await llm_client.generate_content_async(",
                "await llm_client.aio.models.generate_content(",
            )
            return code

        cand_a = _clean_agent_code(cand_a)
        cand_b = _clean_agent_code(cand_b)

        # Validate both compile
        a_valid = True
        b_valid = True
        try:
            compile(cand_a, f"{pattern.pattern_name}_a.py", "exec")
        except SyntaxError:
            a_valid = False
        try:
            compile(cand_b, f"{pattern.pattern_name}_b.py", "exec")
        except SyntaxError:
            b_valid = False

        if a_valid and b_valid:
            # Use LLM to pick the more grounded candidate
            pick_prompt = (
                "Two candidate agent prompts were generated for the same task. "
                "Which is more factually grounded and less likely to fabricate "
                "API names, CLI flags, or technical details?\n\n"
                f"--- CANDIDATE A ---\n{cand_a[:3000]}\n\n"
                f"--- CANDIDATE B ---\n{cand_b[:3000]}\n\n"
                "Reply with ONLY 'A' or 'B'."
            )
            try:
                pick_resp = await generate_with_fallback(
                    client=client,
                    model=model,
                    contents=pick_prompt,
                    config=genai.types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=8,
                    ),
                )
                agent_code = cand_b if "B" in (pick_resp.text or "").upper() else cand_a
            except Exception:  # noqa: BLE001 — best-effort A/B pick; default to cand_a
                agent_code = cand_a  # default to lower-temperature candidate
        elif a_valid:
            agent_code = cand_a
        elif b_valid:
            agent_code = cand_b
        else:
            agent_code = cand_a  # both invalid, let critic catch it

        # Post-generation fact-check: scan ENRICHED_PROMPT for fabricated claims
        agent_code = await _fact_check_agent(agent_code, pattern, client, model)

        # Write agent file
        agent_path = agents_dir / f"{pattern.pattern_name}.py"
        agent_path.write_text(agent_code, encoding="utf-8")

        manifest_agents.append(
            {
                "name": pattern.pattern_name,
                "file": f"agents/{pattern.pattern_name}.py",
                "complexity": resolved_complexity,
                "frequency": pattern.frequency,
                "trigger_type": trigger.get("trigger_type", "attribute_match"),
            }
        )

    # Generate structured attribute rules for programmatic matching
    triggers = await _generate_attribute_rules(
        triggers, patterns_by_name, client, model
    )

    # Generate binary questions for two-stage matching
    triggers = await _generate_binary_questions(
        triggers, patterns_by_name, client, model
    )

    # Compute scope embeddings for semantic matching
    triggers = await _compute_agent_embeddings(triggers, patterns_by_name, client)

    # Add per-user config to triggers (allows per-user threshold tuning)
    triggers["_config"] = {
        "similarity_threshold": 0.45,  # default; can be tuned per user after evaluation
    }

    # Write triggers.json
    triggers_path = user_dir / "triggers.json"
    triggers_path.write_text(json.dumps(triggers, indent=2, ensure_ascii=False))

    # Write manifest.json
    manifest = {
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_sessions_analyzed": 50,
        "agent_count": len(manifest_agents),
        "behavioral_patterns_absorbed": len(behavioral_patterns),
        "has_user_style": bool(user_style),
        "agents": manifest_agents,
    }
    manifest_path = user_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    # Run critic/revision pass
    print(f"  Critic pass ({len(task_patterns)} agents)...", flush=True)
    if not skip_critic and task_patterns:
        critic_summary = await _critic_pass(
            user_id=user_id,
            user_dir=user_dir,
            task_patterns=task_patterns,
            triggers=triggers,
            user_style_text=user_style_text,
            client=client,
            model=model,
        )
        # Re-write triggers.json if any were revised
        if critic_summary.get("triggers_revised", 0) > 0:
            triggers_path.write_text(json.dumps(triggers, indent=2, ensure_ascii=False))
        # Update manifest with critic results
        manifest["critic_pass"] = critic_summary
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    # ── Merge overlapping agents (after critic, before ranking) ──────
    merge_summary = await _merge_overlapping_agents(
        task_patterns=task_patterns,
        triggers=triggers,
        agents_dir=agents_dir,
        manifest=manifest,
        user_style_text=user_style_text,
        user_id=user_id,
        client=client,
        model=model,
    )
    manifest["merge_pass"] = merge_summary

    # Recompute embeddings for merged agents
    patterns_by_name_full = {p.pattern_name: p for p in task_patterns}
    if merge_summary.get("merges"):
        triggers = await _compute_agent_embeddings(
            triggers, patterns_by_name_full, client
        )

    # Persist after merge
    triggers_path.write_text(json.dumps(triggers, indent=2, ensure_ascii=False))
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    # Tier 2: LLM-based quality ranking (after critic pass)
    critic_summary_ref = manifest.get("critic_pass") if not skip_critic else None
    print(
        f"  Ranking {len(task_patterns)} agents (quality threshold {MIN_QUALITY_SCORE}/50)..."
    )
    ranking_summary = await _rank_and_select_agents(
        user_id=user_id,
        user_dir=user_dir,
        task_patterns=task_patterns,
        triggers=triggers,
        manifest=manifest,
        critic_summary=critic_summary_ref,
        user_persona=user_persona,
        user_style_text=user_style_text,
        client=client,
        model=model,
        min_quality_score=MIN_QUALITY_SCORE,
    )
    manifest["ranking_pass"] = ranking_summary
    # Rewrite with dropped agents removed
    triggers_path.write_text(json.dumps(triggers, indent=2, ensure_ascii=False))
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    # ── Coverage validation: check for gaps after ranking ────────────
    selected_agents = [a["name"] for a in manifest["agents"]]
    all_task_patterns = [p for p in patterns if p.pattern_type == "task"]

    gaps = _validate_coverage(selected_agents, all_task_patterns, triggers)
    if gaps:
        print(f"  Coverage gaps found: {[g['dropped_pattern'] for g in gaps]}")
        triggers = await _resolve_gaps(
            gaps, selected_agents, triggers, patterns_by_name_full, client
        )

    # Expand domains for cross-domain users
    triggers = _expand_domains_for_user(triggers, user_persona)

    # Recompute scope embeddings after coverage changes
    if gaps:
        triggers = await _compute_agent_embeddings(
            triggers, patterns_by_name_full, client
        )

    # Record coverage check in manifest
    manifest["coverage_check"] = {
        "gaps_found": len(gaps),
        "gaps_resolved": [g["dropped_pattern"] for g in gaps],
    }

    # ── Validation gate (after coverage, before final output) ────────
    validation_summary = await _run_validation_gate(
        triggers=triggers,
        manifest=manifest,
        agents_dir=agents_dir,
        user_id=user_id,
        client=client,
        model=model,
        user_style_text=user_style_text,
    )
    manifest["validation_gate"] = validation_summary

    # Recompute embeddings if agents were removed
    if validation_summary.get("removed"):
        triggers = await _compute_agent_embeddings(
            triggers, patterns_by_name_full, client
        )

    # Final write of triggers and manifest
    triggers_path.write_text(json.dumps(triggers, indent=2, ensure_ascii=False))
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    return manifest
