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

"""Active memory: checks triggers and invokes mini-agents from user swarms.

Implements the active_mem -> assistant_agent -> active_mem loop.
Four trigger modes:
- attribute_match: Single Flash feature extraction + programmatic rule matching (new)
- llm_match: Two-stage LLM screening (flash parallel + pro tiebreak)
- keyword_and_context: Legacy keyword substring matching
- intent_classification: Legacy intent phrase matching
"""

import asyncio
import inspect
import os
import re
import sys

from google.adk.tools.tool_context import ToolContext

from .swarm_loader import load_swarm

# Add project root to path so analyzer package is importable
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import config as cfg
from analyzer.trigger_schema import (
    build_extraction_prompt,
    match_agent_rules,
    match_agent_rules_with_embedding,
    parse_features,
)

# Feature flag: when False, all matches above similarity threshold fire auto.
# When True, scores between 0.45–0.52 return suggest instead of auto.
SUGGEST_MODE_ENABLED = False

# Confidence threshold (only used when SUGGEST_MODE_ENABLED = True):
# scores above this → auto, scores between 0.45 and this → suggest.
AUTO_CONFIDENCE_THRESHOLD = 0.52

# Invocation log — test harness reads this to know which agent fired.
# Each entry: {"action": "auto"|"suggest"|"none", "agent_name": str|None}
invocation_log: list[dict] = []


def _extract_history(tool_context: ToolContext) -> list[dict]:
    """Extract user/assistant conversation turns from session events."""
    history = []
    session = getattr(tool_context, "session", None)
    if not session:
        return history
    events = getattr(session, "events", None) or []
    for event in events:
        if not hasattr(event, "content") or event.content is None:
            continue
        text_parts = []
        if hasattr(event.content, "parts") and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    text_parts.append(part.text)
        if text_parts:
            role = "user" if getattr(event, "author", "") == "user" else "assistant"
            history.append({"role": role, "content": " ".join(text_parts)})
    return history


# ── LLM-based trigger matching (new) ────────────────────────────────

_SCREEN_PROMPT = """\
Does this user message fall within this agent's scope?

Agent SCOPE (what it handles): {scope}

Agent EXCLUSIONS (what it does NOT handle): {exclusions}

User message: "{user_message}"

Rules:
- Answer YES only if the message is clearly and directly within the SCOPE.
- Answer NO if the message touches on ANY exclusion topic, even partially.
- Answer NO if the message is about a general topic that merely shares
  vocabulary with the scope.
- When in doubt, answer NO.

Answer ONLY "YES" or "NO"."""

_TIEBREAK_PROMPT = """\
A user sent this message:
"{user_message}"

Multiple specialized agents matched. Pick the BEST one, or NONE if the
message doesn't clearly fit any of them.

Candidates:
{candidates_text}

Reply with ONLY the agent name, or "NONE"."""


async def _screen_agent_flash(
    user_message: str, agent_name: str, description: str, client
) -> tuple[str, bool]:
    """Screen one agent against user message using flash model.

    Splits the description into scope and exclusions so the screening
    prompt can emphasize what the agent does NOT handle.

    Returns (agent_name, matched).
    """
    # Split description into scope and exclusions
    scope = description
    exclusions = "None specified"
    for marker in ["Does NOT handle", "Does NOT", "Do NOT use", "NOT:"]:
        if marker in description:
            parts = description.split(marker, 1)
            scope = parts[0].strip().rstrip(".")
            exclusions = marker + parts[1].strip()
            break

    prompt = _SCREEN_PROMPT.format(
        scope=scope, exclusions=exclusions, user_message=user_message
    )
    response = await client.aio.models.generate_content(
        model=cfg.TRIGGER_MODEL, contents=prompt
    )
    return (agent_name, "yes" in response.text.strip().lower())


async def _tiebreak_pro(
    user_message: str, candidates: list[tuple[str, str]], client
) -> str | None:
    """Pick the best agent from multiple candidates using pro model.

    Args:
        candidates: list of (agent_name, description) tuples.

    Returns:
        Winning agent name, or None if no clear winner.
    """
    candidates_text = "\n".join(f"- {name}: {desc}" for name, desc in candidates)
    prompt = _TIEBREAK_PROMPT.format(
        user_message=user_message, candidates_text=candidates_text
    )
    response = await client.aio.models.generate_content(
        model=cfg.REVIEW_MODEL, contents=prompt
    )
    result = response.text.strip().lower()
    if result == "none":
        return None
    for name, _ in candidates:
        if name.lower() in result:
            return name
    return None


async def _evaluate_questionnaires(
    user_message: str,
    scored: list[tuple[str, float]],
    attribute_triggers: dict,
    client,
) -> tuple[str | None, str]:
    """Stage 2 matching: evaluate binary questions for candidate agents.

    Runs questionnaires for all scored agents in parallel via Flash.
    Returns (matched_agent, confidence).
    """
    import asyncio

    from analyzer.trigger_schema import (
        build_questionnaire_eval_prompt,
        score_binary_answers,
    )

    # Collect agents that have binary_questions
    agents_with_questions = []
    for name, emb_score in scored[:5]:  # top 5 max
        questions = attribute_triggers.get(name, {}).get("binary_questions", [])
        if questions:
            agents_with_questions.append((name, emb_score, questions))

    if not agents_with_questions:
        # No questionnaires available — fall back to embedding score
        best_name = scored[0][0]
        return best_name, "high"

    # Evaluate all questionnaires in parallel
    async def _eval_one(name: str, questions: list[dict]) -> tuple[str, float]:
        prompt = build_questionnaire_eval_prompt(user_message, questions)
        try:
            from google.genai import types

            response = await client.aio.models.generate_content(
                model=cfg.TRIGGER_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=256,
                ),
            )
            import json

            text = response.text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                text = "\n".join(lines)
            result = json.loads(text)
            answers = result.get("answers", [])
            ratio = score_binary_answers(answers, questions)
            return name, ratio
        except Exception:  # noqa: BLE001 — best-effort questionnaire eval; 0.0 = no match
            return name, 0.0

    tasks = [_eval_one(name, q) for name, _, q in agents_with_questions]
    questionnaire_results = await asyncio.gather(*tasks)

    # Build combined scores: embedding (0.4) + questionnaire (0.6)
    emb_scores = {name: score for name, score in scored}
    combined = []
    for name, q_ratio in questionnaire_results:
        emb = emb_scores.get(name, 0.0)
        combined_score = 0.4 * emb + 0.6 * q_ratio
        combined.append((name, q_ratio, combined_score))

    # Decision logic
    passing = [(n, qr, cs) for n, qr, cs in combined if qr >= 0.8]

    if len(passing) == 1:
        # Clear winner from questionnaire
        return passing[0][0], "high"
    if len(passing) > 1:
        # Multiple pass — use combined score
        passing.sort(key=lambda x: x[2], reverse=True)
        return passing[0][0], "high"
    # No agent passed questionnaire threshold — escalate to Pro
    candidates = [
        (name, attribute_triggers[name].get("description", ""))
        for name, _ in scored[:3]
    ]
    winner = await _tiebreak_pro(user_message, candidates, client)
    if winner:
        return winner, "low" if SUGGEST_MODE_ENABLED else "high"
    return scored[0][0], "low" if SUGGEST_MODE_ENABLED else "high"


# ── Legacy keyword matching (kept for backward compatibility) ────────


def _score_keyword_trigger(message: str, trigger_config: dict) -> int:
    """Score how well a message matches a keyword_and_context trigger.

    Returns 0 if no match, or a positive score (higher = better match).
    """
    lower = message.lower()
    keywords = trigger_config.get("keywords", [])
    context_hints = trigger_config.get("context_hints", [])
    min_matches = trigger_config.get("min_keyword_matches", 2)

    kw_matches = sum(1 for kw in keywords if kw.lower() in lower)
    ctx_matches = sum(1 for ch in context_hints if ch.lower() in lower)

    is_match = (kw_matches >= min_matches) or (kw_matches >= 1 and ctx_matches >= 1)
    if not is_match:
        return 0
    return kw_matches + ctx_matches


def _match_intent_trigger(message: str, trigger_config: dict) -> bool:
    """Check if message matches an intent_classification trigger."""
    phrases = trigger_config.get("intent_phrases", [])
    lower = message.lower()
    return any(phrase.lower() in lower for phrase in phrases)


# ── Attribute-based feature extraction (new) ─────────────────────────


async def _extract_features_flash(user_message: str, client) -> dict:
    """Extract structured features from user message in one Flash call."""
    from google.genai import types

    prompt = build_extraction_prompt(user_message)
    response = await client.aio.models.generate_content(
        model=cfg.TRIGGER_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
        ),
    )
    return parse_features(response.text)


# ── Task-adaptive style dampening ────────────────────────────────────

_COMPLEX_TASK_SIGNALS = [
    "plan",
    "strategy",
    "pricing",
    "budget",
    "breakdown",
    "itinerary",
    "comparison",
    "analysis",
    "financial",
    "architecture",
    "derivation",
    "proof",
    "implementation",
    "workflow",
    "pipeline",
    "negotiation",
    "comprehensive",
]

_FRAGMENTATION_PHRASES = [
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
    "long comprehensive lists",
    "exhaustive details",
    "multi-part responses",
    "walls of text",
]


def _apply_task_adaptive_style(
    user_style: dict,
    user_message: str,
) -> dict:
    """Dampen style constraints that conflict with complex tasks.

    When the user message signals a task requiring comprehensive output
    (financial plans, pricing strategies, multi-part analysis), override
    style constraints like 'bite-sized' and 'one concept at a time' that
    would force fragmentation.
    """
    msg_lower = user_message.lower()
    complexity_score = sum(1 for signal in _COMPLEX_TASK_SIGNALS if signal in msg_lower)

    if complexity_score < 2:
        return user_style  # Not a complex task, apply style as-is

    adapted = dict(user_style)

    # Override constraints that conflict with comprehensive output
    adapted["_task_override"] = (
        "This is a complex task requiring a comprehensive, complete answer. "
        "Provide the full solution in a single response. Do NOT fragment "
        "into multiple turns, do NOT ask for confirmation between steps, "
        "and do NOT limit yourself to short responses. The user expects "
        "a thorough, actionable answer."
    )

    # Surgically remove conflicting phrases instead of blanking entire keys
    for key in ("response_length", "format", "avoid", "follow_up"):
        val = adapted.get(key, "")
        if isinstance(val, str) and val:
            cleaned = val
            for phrase in _FRAGMENTATION_PHRASES:
                # Case-insensitive removal of the phrase
                idx = cleaned.lower().find(phrase)
                while idx != -1:
                    cleaned = cleaned[:idx] + cleaned[idx + len(phrase) :]
                    idx = cleaned.lower().find(phrase)
            # Clean up leftover punctuation artifacts (", ,", leading/trailing commas)
            cleaned = cleaned.strip()
            cleaned = cleaned.strip(",;").strip()
            # Collapse multiple commas/semicolons
            while ",," in cleaned:
                cleaned = cleaned.replace(",,", ",")
            while ";;" in cleaned:
                cleaned = cleaned.replace(";;", ";")
            adapted[key] = cleaned

    # Clean empty keys
    adapted = {k: v for k, v in adapted.items() if v}

    return adapted


# ── Response post-processing ──────────────────────────────────────────

_CONVERSATIONAL_TAILS = [
    r"\n*(?:is there anything else|anything else)[^\n]*$",
    r"\n*(?:let me know if|feel free to)[^\n]*$",
    r"\n*(?:happy to help|glad to help)[^\n]*$",
    r"\n*(?:hope this helps|hope that helps)[^\n]*$",
]


def _strip_conversational_tails(response: str) -> str:
    """Remove trailing conversational filler from agent responses."""
    for pattern in _CONVERSATIONAL_TAILS:
        response = re.sub(pattern, "", response, flags=re.IGNORECASE)
    return response.rstrip()


# Phrases that indicate the agent fabricated prior conversation context.
# Only checked on the first turn (no history) to avoid false positives
# on legitimate multi-turn conversations.
_HALLUCINATION_MARKERS = [
    r"as we (?:were |just )?discuss",
    r"(?:continuing|picking up) (?:from )?where we",
    r"your (?:previous )?message was cut off",
    r"it (?:seems|appears|looks like) (?:your|the) (?:previous )?(?:message|thought|response) was (?:cut off|truncated|incomplete)",
    r"you mentioned (?:earlier|before|in your (?:draft|previous))",
    r"(?:as|like) (?:I|we) (?:mentioned|noted|outlined) (?:earlier|before|above|previously)",
]


def _has_hallucinated_context(response: str) -> bool:
    """Check if a first-turn response fabricates prior conversation context."""
    # Only check the first ~500 chars where these phrases typically appear
    head = response[:500].lower()
    return any(re.search(p, head) for p in _HALLUCINATION_MARKERS)


def _ensure_code_fences(response: str) -> str:
    """Wrap unfenced code blocks in markdown fences.

    Detects code-like content (indented blocks, function definitions,
    import statements) that is not already inside ``` fences.
    """
    if "```" in response:
        return response  # Already has fences, don't double-wrap

    lines = response.split("\n")
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return response

    code_indicators = sum(
        1
        for l in non_empty
        if l.strip().startswith(
            (
                "def ",
                "class ",
                "import ",
                "from ",
                "async ",
                "await ",
                "return ",
                "if ",
                "for ",
                "while ",
                "try:",
                "except",
                "#",
                "@",
                "RUN ",
                "FROM ",
                "COPY ",
                "ENV ",
                "EXPOSE ",
                "CMD ",
                "WORKDIR ",
            )
        )
        or l.startswith(("    ", "\t"))
    )

    if code_indicators / len(non_empty) > 0.4:
        lang = "python"
        if any(kw in response for kw in ("FROM ", "RUN ", "COPY ", "CMD [")):
            lang = "dockerfile"
        elif any(kw in response for kw in ("SELECT ", "INSERT ", "CREATE TABLE")):
            lang = "sql"
        return f"```{lang}\n{response}\n```"

    return response


# ── Main entry point ─────────────────────────────────────────────────


async def check_and_invoke_swarm(user_message: str, tool_context: ToolContext) -> dict:
    """Check if a mini-agent should handle this message.

    Called as an ADK tool by the augmented assistant. Loads the current
    user's swarm, checks triggers, and either auto-invokes or suggests.

    Supports four trigger types:
    - attribute_match: 1 Flash feature extraction + programmatic rules (preferred)
    - llm_match: parallel flash screening + pro tiebreak (legacy)
    - keyword_and_context: substring keyword matching (legacy)
    - intent_classification: intent phrase matching (legacy)

    Args:
        user_message: The user's current message.
        tool_context: ADK tool context (provides user_id, session state).

    Returns:
        One of:
        - {"action": "auto", "agent_name": str, "response": str}
        - {"action": "suggest", "agent_name": str, "suggestion": str}
        - {"action": "none"}
    """
    user_id = tool_context.user_id
    swarm = load_swarm(user_id)

    if not swarm["triggers"]:
        invocation_log.append({"action": "none", "agent_name": None})
        return {"action": "none"}

    client = cfg.new_client()

    # ── Confirmation detection: user said "yes" to a previous suggestion ──
    confirmation_words = {
        "yes",
        "sure",
        "go ahead",
        "please",
        "do it",
        "yeah",
        "ok",
        "okay",
        "yep",
        "absolutely",
        "definitely",
    }
    if (
        SUGGEST_MODE_ENABLED
        and invocation_log
        and invocation_log[-1].get("action") == "suggest"
        and any(w in user_message.lower().split() for w in confirmation_words)
    ):
        last_suggested = invocation_log[-1]["agent_name"]
        agent_module = swarm["agents"].get(last_suggested)
        if agent_module is not None:
            # Force-execute the previously suggested agent
            styled_message = user_message
            user_style = swarm.get("user_style")
            if user_style:
                user_style = _apply_task_adaptive_style(user_style, user_message)
                style_instructions = "\n".join(
                    f"- {k}: {v}" for k, v in user_style.items()
                )
                styled_message = (
                    f"[STYLE INSTRUCTIONS — follow these for your response format:\n"
                    f"{style_instructions}]\n\n"
                    f"{user_message}"
                )
            try:
                history = _extract_history(tool_context)
                sig = inspect.signature(agent_module.execute)
                if "history" in sig.parameters:
                    coro = agent_module.execute(styled_message, client, history=history)
                else:
                    coro = agent_module.execute(styled_message, client)
                response = await asyncio.wait_for(coro, timeout=120.0)
                response = _strip_conversational_tails(response)
                response = _ensure_code_fences(response)
                invocation_log.append({"action": "auto", "agent_name": last_suggested})
                return {
                    "action": "auto",
                    "agent_name": last_suggested,
                    "response": response,
                }
            except Exception as e:  # noqa: BLE001 — generated agent code can raise anything
                print(f"ERROR: confirmed agent {last_suggested} execute() failed: {e}")
                # Fall through to normal matching

    # ── Separate triggers by type ────────────────────────────────
    attribute_triggers = {}  # agent_name -> trigger_config (new)
    llm_triggers = {}  # agent_name -> description
    keyword_triggers = {}  # agent_name -> trigger_config
    intent_triggers = {}  # agent_name -> trigger_config

    # Read per-user config (e.g., similarity_threshold)
    user_config = swarm["triggers"].get("_config", {})
    user_similarity_threshold = user_config.get("similarity_threshold")

    for agent_name, trigger_config in swarm["triggers"].items():
        if agent_name == "_config":
            continue  # skip config entry
        trigger_type = trigger_config.get("trigger_type", "keyword_and_context")
        if trigger_type == "attribute_match":
            attribute_triggers[agent_name] = trigger_config
        elif trigger_type == "llm_match":
            llm_triggers[agent_name] = trigger_config.get("description", "")
        elif trigger_type == "keyword_and_context":
            keyword_triggers[agent_name] = trigger_config
        elif trigger_type == "intent_classification":
            intent_triggers[agent_name] = trigger_config

    matched_agent = None
    match_confidence = "high"  # default; overridden by embedding scoring

    # ── Stage 1: Attribute + Embedding matching ─────────────────────
    all_have_embeddings = False
    if attribute_triggers:
        features = await _extract_features_flash(user_message, client)

        # Check if ALL agents have pre-computed scope embeddings
        all_have_embeddings = all(
            config.get("scope_embedding") for config in attribute_triggers.values()
        )
        has_embeddings = any(
            config.get("scope_embedding") for config in attribute_triggers.values()
        )

        if has_embeddings:
            # Embed user message (1 API call, ~10x cheaper than Flash)
            embed_response = await client.aio.models.embed_content(
                model=cfg.EMBED_MODEL,
                contents=user_message[:2000],
            )
            message_embedding = list(embed_response.embeddings[0].values)

            scored = []
            for name, config in attribute_triggers.items():
                rules = config.get("rules", {})
                scope_emb = config.get("scope_embedding")
                if not scope_emb:
                    # Fallback: no embedding, use legacy keyword matching
                    if match_agent_rules(features, rules, raw_message=user_message):
                        scored.append((name, 0.5))
                    continue

                match_kwargs = {}
                if user_similarity_threshold is not None:
                    match_kwargs["similarity_threshold"] = user_similarity_threshold
                score = match_agent_rules_with_embedding(
                    features,
                    rules,
                    message_embedding,
                    scope_emb,
                    **match_kwargs,
                )
                if score is not None:
                    scored.append((name, score))

                # Secondary domain fallback: if the message looks like a
                # code request but Flash classified it as a non-software
                # domain, retry with software_engineering to catch
                # cross-domain code requests (e.g., Dockerfile).
                if (
                    score is None
                    and features.get("domain") not in ("software_engineering",)
                    and features.get("task_type")
                    in ("create_generate", "explain_teach")
                    and features.get("output_format") in ("code", "mixed")
                ):
                    secondary_features = dict(features)
                    secondary_features["domain"] = "software_engineering"
                    score2 = match_agent_rules_with_embedding(
                        secondary_features,
                        rules,
                        message_embedding,
                        scope_emb,
                        **match_kwargs,
                    )
                    if score2 is not None:
                        scored.append((name, score2))

            if scored:
                scored.sort(key=lambda x: x[1], reverse=True)
                best_name, best_score = scored[0]

                if len(scored) == 1:
                    # Only one candidate — no ambiguity
                    matched_agent = best_name
                    if SUGGEST_MODE_ENABLED:
                        match_confidence = (
                            "high" if best_score >= AUTO_CONFIDENCE_THRESHOLD else "low"
                        )
                    else:
                        match_confidence = "high"
                else:
                    # Stage 2: Binary questionnaire for disambiguation
                    matched_agent, match_confidence = await _evaluate_questionnaires(
                        user_message, scored, attribute_triggers, client
                    )
        else:
            # No embeddings stored — legacy keyword matching
            candidates = []
            for name, config in attribute_triggers.items():
                rules = config.get("rules", {})
                if match_agent_rules(features, rules, raw_message=user_message):
                    candidates.append((name, config.get("description", "")))

            if len(candidates) == 1:
                matched_agent = candidates[0][0]
            elif len(candidates) >= 2:
                matched_agent = await _tiebreak_pro(user_message, candidates, client)

    # ── Legacy fallback stages (only if NOT all agents have embeddings) ──
    # When all agents have scope_embeddings, the embedding path is
    # authoritative — skip keyword/intent/LLM fallbacks to avoid
    # false positives from substring matching.
    if not all_have_embeddings:
        # ── Fallback: LLM-based matching (parallel flash screening) ───
        if matched_agent is None and llm_triggers:
            screening_tasks = [
                _screen_agent_flash(user_message, name, desc, client)
                for name, desc in llm_triggers.items()
            ]
            results = await asyncio.gather(*screening_tasks)
            candidates = [
                (name, llm_triggers[name]) for name, matched in results if matched
            ]

            if len(candidates) == 1:
                matched_agent = candidates[0][0]
            elif len(candidates) >= 2:
                matched_agent = await _tiebreak_pro(user_message, candidates, client)

        # ── Fallback: keyword matching (for legacy triggers) ─────────
        if matched_agent is None and keyword_triggers:
            best_score = 0
            for agent_name, trigger_config in keyword_triggers.items():
                score = _score_keyword_trigger(user_message, trigger_config)
                if score > best_score:
                    best_score = score
                    matched_agent = agent_name

        # ── Fallback: intent matching (for legacy triggers) ──────────
        if matched_agent is None and intent_triggers:
            for agent_name, trigger_config in intent_triggers.items():
                if _match_intent_trigger(user_message, trigger_config):
                    matched_agent = agent_name
                    break

    # ── No match ─────────────────────────────────────────────────
    if matched_agent is None:
        invocation_log.append({"action": "none", "agent_name": None})
        return {"action": "none"}

    # ── Load and invoke the matched agent ────────────────────────
    agent_module = swarm["agents"].get(matched_agent)
    if agent_module is None:
        invocation_log.append({"action": "none", "agent_name": matched_agent})
        return {"action": "none"}

    # ── Low confidence → suggest without executing (only when enabled) ──
    if match_confidence == "low" and SUGGEST_MODE_ENABLED:
        # Build user-facing suggestion from agent name (not raw description)
        friendly_name = matched_agent.replace("_", " ")
        invocation_log.append({"action": "suggest", "agent_name": matched_agent})
        return {
            "action": "suggest",
            "agent_name": matched_agent,
            "suggestion": f"help you with {friendly_name}",
        }

    # ── High confidence → execute agent silently ──────────────────
    # Inject user style as a prefix to the user message so the agent
    # respects the user's communication preferences.
    # Task-adaptive dampening removes conflicting constraints for complex tasks.
    styled_message = user_message
    user_style = swarm.get("user_style")
    if user_style:
        user_style = _apply_task_adaptive_style(user_style, user_message)
        style_instructions = "\n".join(f"- {k}: {v}" for k, v in user_style.items())
        styled_message = (
            f"[STYLE INSTRUCTIONS — follow these for your response format:\n"
            f"{style_instructions}]\n\n"
            f"{user_message}"
        )

    try:
        history = _extract_history(tool_context)
        sig = inspect.signature(agent_module.execute)
        if "history" in sig.parameters:
            coro = agent_module.execute(styled_message, client, history=history)
        else:
            coro = agent_module.execute(styled_message, client)
        response = await asyncio.wait_for(coro, timeout=120.0)
    except asyncio.TimeoutError:
        print(f"ERROR: agent {matched_agent} execute() timed out (120s)")
        invocation_log.append(
            {"action": "error", "agent_name": matched_agent, "error": "timeout"}
        )
        return {"action": "error", "agent_name": matched_agent, "error": "timeout"}
    except Exception as e:  # noqa: BLE001 — generated agent code can raise anything
        print(f"ERROR: agent {matched_agent} execute() failed: {e}")
        invocation_log.append(
            {"action": "error", "agent_name": matched_agent, "error": str(e)}
        )
        return {"action": "error", "agent_name": matched_agent, "error": str(e)}

    # Post-process: strip conversational tails and ensure code fences
    response = _strip_conversational_tails(response)
    response = _ensure_code_fences(response)

    # Safety: detect hallucinated prior-conversation context on first turn.
    # If the agent fabricates "as we discussed" / "your message was cut off"
    # when there is no history, fall back to "none" so the base agent handles it.
    if not history and _has_hallucinated_context(response):
        print(
            f"WARNING: agent {matched_agent} hallucinated prior context on first turn, falling back"
        )
        invocation_log.append(
            {"action": "hallucination_fallback", "agent_name": matched_agent}
        )
        return {"action": "none"}

    invocation_log.append({"action": "auto", "agent_name": matched_agent})
    return {
        "action": "auto",
        "agent_name": matched_agent,
        "response": response,
    }
