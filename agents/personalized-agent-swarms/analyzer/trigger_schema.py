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

"""Structured attribute-based trigger matching.

Defines the feature schema used for message classification, the prompt
for single-call feature extraction, and the programmatic matching logic.

Shared by:
- swarm_generator.py  (generation-time: builds agent rules)
- active_mem.py       (runtime: extracts features + matches rules)
"""

import json

import numpy as np

# ── Feature Schema ──────────────────────────────────────────────────

DOMAIN_LABELS = [
    "software_engineering",
    "devops_infrastructure",
    "data_science_ml",
    "marketing_advertising",
    "business_strategy",
    "finance_accounting",
    "food_beverage",
    "travel_leisure",
    "academic_research",
    "consumer_lifestyle",
    "human_resources",
    "legal_compliance",
    "other",
]

TASK_TYPE_LABELS = [
    "create_generate",
    "debug_troubleshoot",
    "analyze_evaluate",
    "explain_teach",
    "plan_strategize",
    "configure_setup",
    "find_search",
    "format_structure",
    "negotiate_communicate",
    "other",
]

SPECIFICITY_LABELS = ["generic", "domain_aware", "specialist"]

OUTPUT_FORMAT_LABELS = ["code", "structured_text", "narrative", "calculation", "mixed"]

SCOPE_LABELS = ["single_item", "comparison", "comprehensive", "iterative"]

SPECIFICITY_ORDER = {"generic": 0, "domain_aware": 1, "specialist": 2}

# ── Feature Extraction Prompt ───────────────────────────────────────

_FEATURE_EXTRACTION_PROMPT = """\
Analyze this user message and extract structured attributes.

User message: "{user_message}"

Answer each question with EXACTLY one of the provided labels \
(or a value of the specified type).

1. domain: What primary domain does this message belong to?
   Labels: {domain_labels}

2. task_type: What type of task is the user requesting?
   Labels: {task_type_labels}

3. specificity: How domain-specific is this message?
   Labels: {specificity_labels}

4. output_format: What format does the user expect?
   Labels: {output_format_labels}

5. scope: What is the scope of the request?
   Labels: {scope_labels}

6. topic_keywords: Extract 3-8 specific topic keywords from the message \
(as a JSON array of lowercase strings).

7. action_object: What is the primary object/target of the action? \
(short phrase, e.g. "Dockerfile", "menu prices", "literature review")

Return ONLY a JSON object with keys: domain, task_type, specificity, \
output_format, scope, topic_keywords, action_object."""


def build_extraction_prompt(user_message: str) -> str:
    """Build the feature extraction prompt for a single Flash LLM call."""
    return _FEATURE_EXTRACTION_PROMPT.format(
        user_message=user_message[:2000],
        domain_labels=", ".join(DOMAIN_LABELS),
        task_type_labels=", ".join(TASK_TYPE_LABELS),
        specificity_labels=", ".join(SPECIFICITY_LABELS),
        output_format_labels=", ".join(OUTPUT_FORMAT_LABELS),
        scope_labels=", ".join(SCOPE_LABELS),
    )


def parse_features(response_text: str) -> dict:
    """Parse the LLM response into a features dict.

    Returns a safe default dict if parsing fails.
    """
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        features = json.loads(text)
        # Normalize topic_keywords to list of strings
        if not isinstance(features.get("topic_keywords"), list):
            features["topic_keywords"] = []
        features["topic_keywords"] = [
            str(kw).lower() for kw in features["topic_keywords"]
        ]
        if not isinstance(features.get("action_object"), str):
            features["action_object"] = ""
        return features
    except (json.JSONDecodeError, TypeError):
        return {
            "domain": "other",
            "task_type": "other",
            "specificity": "generic",
            "output_format": "narrative",
            "scope": "single_item",
            "topic_keywords": [],
            "action_object": "",
        }


# ── Programmatic Matching ───────────────────────────────────────────


def match_agent_rules(features: dict, rules: dict, raw_message: str = "") -> bool:
    """Check if extracted features match an agent's rules.

    Returns True if the agent should be considered a candidate, False
    otherwise.  This is a binary pass/fail filter — no scoring.  When
    multiple agents pass, the Pro LLM tiebreaker selects the best one.

    Args:
        features: Extracted features from Flash LLM.
        rules: Agent's matching rules.
        raw_message: Original user message for broader keyword matching.
    """
    # 1. Domain check (required)
    if "domain" in rules and features.get("domain") not in rules["domain"]:
        return False

    # 2. Task type check (required)
    if "task_type" in rules and features.get("task_type") not in rules["task_type"]:
        return False

    # 3. Specificity floor (required)
    if "min_specificity" in rules:
        min_level = SPECIFICITY_ORDER.get(rules["min_specificity"], 0)
        actual_level = SPECIFICITY_ORDER.get(features.get("specificity", "generic"), 0)
        if actual_level < min_level:
            return False

    # 4. Keyword matching (required if present)
    # Check against both extracted features AND raw user message
    all_text_lower = " ".join(features.get("topic_keywords", []))
    all_text_lower += " " + (features.get("action_object") or "").lower()
    all_text_lower += " " + raw_message.lower()

    if "require_any_keyword" in rules:
        kw_matches = sum(
            1 for kw in rules["require_any_keyword"] if kw.lower() in all_text_lower
        )
        if kw_matches == 0:
            return False

    # 5. Exclusion check (required if present)
    if "exclude_keywords" in rules:
        for ekw in rules["exclude_keywords"]:
            if ekw.lower() in all_text_lower:
                return False

    # 6. Output format check (optional — does not reject)
    # Kept for future use but not a hard filter

    return True


# ── Embedding-Based Matching ───────────────────────────────────────

EMBEDDING_SIMILARITY_THRESHOLD = 0.45
EMBEDDING_TIEBREAK_GAP = 0.05

# Penalties applied when domain/task_type don't match agent rules.
# These replace the old hard binary rejection with soft scoring.
DOMAIN_MISMATCH_PENALTY = 0.15
TASK_TYPE_MISMATCH_PENALTY = 0.10


def _cosine_similarity(
    vec_a: list[float],
    vec_b: list[float],
) -> float:
    """Compute cosine similarity between two vectors."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b) + 1e-9
    return float(dot / norm)


def match_agent_rules_with_embedding(
    features: dict,
    rules: dict,
    message_embedding: list[float],
    scope_embedding: list[float],
    similarity_threshold: float = EMBEDDING_SIMILARITY_THRESHOLD,
) -> float | None:
    """Soft attribute filter + embedding cosine similarity score.

    Domain and task_type mismatches apply scoring penalties instead of
    binary rejection, allowing cross-domain code requests (e.g.,
    Dockerfile requests matching a code-example agent) to still match
    if the embedding similarity is high enough.  Specificity floor
    remains a hard reject (rarely triggers, protects against noise).

    Returns:
        Adjusted similarity score if agent passes filters and threshold.
        None if rejected by specificity floor or below threshold.
    """
    score_penalty = 0.0

    # 1. Domain check — penalty instead of hard rejection
    if "domain" in rules and features.get("domain") not in rules["domain"]:
        score_penalty += DOMAIN_MISMATCH_PENALTY

    # 2. Task type check — penalty instead of hard rejection
    if "task_type" in rules and features.get("task_type") not in rules["task_type"]:
        score_penalty += TASK_TYPE_MISMATCH_PENALTY

    # 3. Specificity floor — keep as hard reject
    if "min_specificity" in rules:
        min_level = SPECIFICITY_ORDER.get(rules["min_specificity"], 0)
        actual_level = SPECIFICITY_ORDER.get(features.get("specificity", "generic"), 0)
        if actual_level < min_level:
            return None

    # 4. Embedding similarity
    similarity = _cosine_similarity(message_embedding, scope_embedding)

    # Apply penalty
    adjusted_score = similarity - score_penalty

    if adjusted_score < similarity_threshold:
        return None

    return adjusted_score


# ── Rule Validation ─────────────────────────────────────────────────


def validate_rules(rules: dict) -> list[str]:
    """Validate agent matching rules and return a list of errors."""
    errors = []

    if "domain" in rules:
        for d in rules["domain"]:
            if d not in DOMAIN_LABELS:
                errors.append(f"Unknown domain label: {d}")

    if "task_type" in rules:
        for t in rules["task_type"]:
            if t not in TASK_TYPE_LABELS:
                errors.append(f"Unknown task_type label: {t}")

    if (
        "min_specificity" in rules
        and rules["min_specificity"] not in SPECIFICITY_LABELS
    ):
        errors.append(f"Unknown specificity label: {rules['min_specificity']}")

    if "require_any_keyword" in rules and (
        not isinstance(rules["require_any_keyword"], list)
        or len(rules["require_any_keyword"]) == 0
    ):
        errors.append("require_any_keyword must be a non-empty list")

    if "exclude_keywords" in rules and not isinstance(rules["exclude_keywords"], list):
        errors.append("exclude_keywords must be a list")

    return errors


# ── Rule Generation Prompt (for swarm_generator.py) ─────────────────

ATTRIBUTE_RULES_PROMPT = """\
You are generating structured matching rules for a set of specialized \
mini-agents belonging to the same user. These rules are used as COARSE \
FILTERS before semantic embedding similarity scoring. They do NOT need \
to be precise — the embedding score is the primary matching signal.

Available feature dimensions:
- domain labels: {domain_labels}
- task_type labels: {task_type_labels}
- output_format labels: {output_format_labels}
- min_specificity: generic | domain_aware | specialist

For each agent below, provide a rules object with:
1. domain: list of domain labels this agent handles (1-3 labels). \
For agents that handle cross-domain requests (e.g., a "code example" \
agent for a user who works with both Python and Google Cloud), include ALL \
relevant domains.
2. task_type: list of task_type labels this agent handles (1-3 labels). \
Be inclusive — if an agent might handle both "create_generate" and \
"debug_troubleshoot" requests, include both.
3. output_format: (optional) list of expected output formats
4. min_specificity: minimum specificity level. Use "generic" as the \
default. Only use "domain_aware" for agents that should NOT fire on \
casual or surface-level questions about the topic. NEVER use "specialist" \
— it rejects most real user messages.

NOTE: Do NOT include require_any_keyword or exclude_keywords. \
Keyword matching has been replaced by embedding-based semantic similarity.

Agents:
{agents_text}

Return a JSON object mapping agent_name -> rules object.
"""


def build_attribute_rules_prompt(agents_text: str) -> str:
    """Build the prompt that generates structured rules for all agents."""
    return ATTRIBUTE_RULES_PROMPT.format(
        domain_labels=", ".join(DOMAIN_LABELS),
        task_type_labels=", ".join(TASK_TYPE_LABELS),
        output_format_labels=", ".join(OUTPUT_FORMAT_LABELS),
        agents_text=agents_text,
    )


# ── Binary Questionnaire (Stage 2 matching) ──────────────────────────

BINARY_QUESTIONS_PROMPT = """\
You are generating discriminating yes/no questions for a set of specialized \
mini-agents. These questions are used as a SECOND-STAGE FILTER after \
embedding similarity scoring, to disambiguate between agents with overlapping \
domains.

Each question must:
1. Be answerable from the user message alone (no external context needed)
2. Test whether the user's request falls within THIS agent's specific scope
3. Distinguish this agent from the other agents listed below

Generate 3-5 binary questions per agent. Each question has an expected \
answer ("yes" or "no") that would indicate the message belongs to this agent.

Focus on CONTRASTIVE questions — ones where the answer differs across agents. \
For example, if agent A handles Docker and agent B handles CI/CD, a good \
question for agent A would be "Is the user asking about container images, \
Dockerfiles, or docker-compose?" (expected: yes).

Agents:
{agents_text}

Return a JSON object mapping agent_name to a list of question objects:
{{
  "agent_name": [
    {{"question": "Is the user asking about X?", "expected_answer": "yes"}},
    {{"question": "Is this about Y?", "expected_answer": "no"}}
  ]
}}
"""


def build_binary_questions_prompt(agents_text: str) -> str:
    """Build the prompt that generates binary questions for all agents."""
    return BINARY_QUESTIONS_PROMPT.format(agents_text=agents_text)


def build_questionnaire_eval_prompt(
    user_message: str,
    questions: list[dict],
) -> str:
    """Build a prompt to evaluate binary questions against a user message.

    All questions for one agent are evaluated in a single Flash call.
    Returns a prompt that asks the LLM to answer each question yes/no.
    """
    q_lines = "\n".join(f"{i + 1}. {q['question']}" for i, q in enumerate(questions))
    return (
        f'Given this user message:\n"{user_message}"\n\n'
        f"Answer each question with ONLY 'yes' or 'no':\n{q_lines}\n\n"
        f'Return JSON: {{"answers": ["yes"|"no", ...]}}'
    )


def score_binary_answers(
    answers: list[str],
    questions: list[dict],
) -> float:
    """Compute match ratio between actual answers and expected answers.

    Returns 0.0 to 1.0 — fraction of questions where the actual answer
    matches the expected answer.
    """
    if not questions or not answers:
        return 0.0

    matches = 0
    total = min(len(answers), len(questions))
    for i in range(total):
        actual = answers[i].lower().strip()
        expected = questions[i].get("expected_answer", "").lower().strip()
        if actual == expected:
            matches += 1

    return matches / total if total > 0 else 0.0
