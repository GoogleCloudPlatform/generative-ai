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

"""Shared trigger matching logic for validation and runtime.

Extracts the core message-to-agent matching pipeline so it can be used by:
- swarm_generator.py  (validation gate during generation)
- active_mem.py       (runtime agent selection)

Uses the same embedding-based matching as active_mem.py without
requiring ADK ToolContext or swarm_loader.
"""

import asyncio

import config as cfg
from analyzer.trigger_schema import (
    build_extraction_prompt,
    build_questionnaire_eval_prompt,
    match_agent_rules_with_embedding,
    parse_features,
    score_binary_answers,
)
from google import genai
from google.genai import types as genai_types


async def extract_features(user_message: str, client: genai.Client) -> dict:
    """Extract structured features from user message in one Flash call."""
    prompt = build_extraction_prompt(user_message)
    response = await client.aio.models.generate_content(
        model=cfg.TRIGGER_MODEL,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
        ),
    )
    return parse_features(response.text)


async def embed_message(user_message: str, client: genai.Client) -> list[float]:
    """Embed a user message using text-embedding-005."""
    response = await client.aio.models.embed_content(
        model=cfg.EMBED_MODEL,
        contents=user_message[:2000],
    )
    return list(response.embeddings[0].values)


async def match_message_to_agent(
    message: str,
    triggers: dict,
    client: genai.Client,
    similarity_threshold: float | None = None,
) -> str | None:
    """Run the full trigger matching pipeline. Returns agent name or None.

    Implements the same logic as active_mem.py's attribute+embedding path:
    1. Extract features via Flash
    2. Embed user message
    3. Score all agents with soft penalties
    4. Tiebreak if top scores are within EMBEDDING_TIEBREAK_GAP

    Args:
        message: The user message to match.
        triggers: Dict of agent_name -> trigger_config (from triggers.json).
        client: Google Cloud genai client.
        similarity_threshold: Override per-user threshold (from _config).

    Returns:
        Name of matched agent, or None.
    """
    # Read per-user config
    user_config = triggers.get("_config", {})
    if similarity_threshold is None:
        similarity_threshold = user_config.get("similarity_threshold")

    # Filter to real agent entries (skip _config)
    agent_triggers = {
        name: config
        for name, config in triggers.items()
        if name != "_config" and config.get("scope_embedding")
    }

    if not agent_triggers:
        return None

    # Extract features + embed message concurrently
    features, message_embedding = await asyncio.gather(
        extract_features(message, client),
        embed_message(message, client),
    )

    # Score all agents
    scored = []
    for name, config in agent_triggers.items():
        rules = config.get("rules", {})
        scope_emb = config.get("scope_embedding")
        if not scope_emb:
            continue

        match_kwargs = {}
        if similarity_threshold is not None:
            match_kwargs["similarity_threshold"] = similarity_threshold

        score = match_agent_rules_with_embedding(
            features,
            rules,
            message_embedding,
            scope_emb,
            **match_kwargs,
        )
        if score is not None:
            scored.append((name, score))

    if not scored:
        return None

    scored.sort(key=lambda x: x[1], reverse=True)
    best_name, _ = scored[0]

    if len(scored) == 1:
        return best_name

    # Stage 2: Binary questionnaire for disambiguation
    matched, _ = await _evaluate_questionnaires(message, scored, agent_triggers, client)
    return matched


async def _evaluate_questionnaires(
    user_message: str,
    scored: list[tuple[str, float]],
    attribute_triggers: dict,
    client: genai.Client,
) -> tuple[str | None, str]:
    """Stage 2 matching: evaluate binary questions for candidate agents.

    Runs questionnaires for all scored agents in parallel via Flash.
    Returns (matched_agent, confidence).
    """
    import json as _json

    # Collect agents that have binary_questions
    agents_with_questions = []
    for name, emb_score in scored[:5]:  # top 5 max
        questions = attribute_triggers.get(name, {}).get("binary_questions", [])
        if questions:
            agents_with_questions.append((name, emb_score, questions))

    if not agents_with_questions:
        # No questionnaires available — fall back to embedding score
        return scored[0][0], "high"

    # Evaluate all questionnaires in parallel
    async def _eval_one(name: str, questions: list[dict]) -> tuple[str, float]:
        prompt = build_questionnaire_eval_prompt(user_message, questions)
        try:
            response = await client.aio.models.generate_content(
                model=cfg.TRIGGER_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=256,
                ),
            )
            text = response.text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                text = "\n".join(lines)
            result = _json.loads(text)
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
        return passing[0][0], "high"
    if len(passing) > 1:
        passing.sort(key=lambda x: x[2], reverse=True)
        return passing[0][0], "high"
    # No agent passed questionnaire threshold — escalate to Pro
    candidates = [
        (name, attribute_triggers[name].get("description", ""))
        for name, _ in scored[:3]
    ]
    winner = await _tiebreak_pro(user_message, candidates, client)
    if winner:
        return winner, "low"
    return scored[0][0], "low"


async def _tiebreak_pro(
    user_message: str,
    candidates: list[tuple[str, str]],
    client: genai.Client,
) -> str | None:
    """Pick the best agent from multiple close candidates using Pro model."""
    candidates_text = "\n".join(f"- {name}: {desc}" for name, desc in candidates)
    prompt = (
        f'A user sent this message:\n"{user_message}"\n\n'
        f"Multiple specialized agents matched. Pick the BEST one, or NONE if the\n"
        f"message doesn't clearly fit any of them.\n\nCandidates:\n{candidates_text}\n\n"
        f'Reply with ONLY the agent name, or "NONE".'
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
