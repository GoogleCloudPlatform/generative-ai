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

"""Extract recurring intent patterns from a user's conversation history.

Uses Gemini 3.1 Pro to analyze session logs and identify patterns
that appear across multiple sessions.
"""

import json
from dataclasses import dataclass

import config as cfg
from google import genai

_EXTRACTION_PROMPT = """\
You are analyzing conversational history for a single user to identify
recurring behavioral patterns.

Below are {batch_size} conversation sessions from user "{user_id}".
Each session has a stated intent, a sequence of turns, and metadata.

For each RECURRING pattern you observe (appearing in 2+ sessions in this
batch), extract:

1. pattern_name: short snake_case name (must be a valid Python identifier)
2. description: 1-2 sentences describing what the user is trying to do
3. frequency: how many sessions in THIS BATCH match this pattern
4. trigger_keywords: list of 10-15 GENERALIZABLE single words or very
   short phrases (2-3 words max) that indicate this intent category.
   IMPORTANT: Do NOT copy exact phrases from conversations. Instead,
   extract the CATEGORY-LEVEL vocabulary. For example:
   - BAD: "Getting a TypeError on line 42", "asyncio.gather swallowing exceptions"
   - GOOD: "error", "exception", "traceback", "debug", "TypeError", "crash", "stack trace"
   These keywords will be used for substring matching against FUTURE
   messages, so they must generalize beyond the training data.
5. trigger_context_hints: list of 5-8 domain words that disambiguate this
   pattern from unrelated topics. For example, a Python debugging pattern
   should have hints like "python", "flask", "django", "handler" — NOT
   generic words like "describes", "specific", "problem".
6. typical_flow: ordered list of 3-6 steps showing how the conversation
   typically unfolds
7. user_preferences: object with keys like "detail_level", "format",
   "tone", "follow_up_behavior" — specific preferences this user
   consistently shows
8. complexity: "static" if a single enriched prompt would suffice, or
   "dynamic" if the pattern requires multi-step execution
9. pattern_type: "task" if this pattern is about WHAT the user wants to
   accomplish (e.g., financial planning, hiring, debugging code, writing
   copy), or "behavioral" if it is about HOW the user communicates
   (e.g., sending incomplete messages, getting overwhelmed by long
   responses, asking for simplification, cutting off mid-sentence).
   Most patterns should be "task". Only classify as "behavioral" if the
   pattern describes a communication style rather than a goal or topic.

Return a JSON array of pattern objects. Only include patterns you are
confident about — do not guess.

<sessions>
{sessions_json}
</sessions>
"""


@dataclass
class Pattern:
    """A recurring intent pattern extracted from conversation history."""

    pattern_name: str
    description: str
    frequency: int
    trigger_signals: list[str]  # generalizable keywords
    trigger_context_hints: list[str]  # domain-specific disambiguation words
    typical_flow: list[str]
    user_preferences: dict
    complexity: str  # "static" or "dynamic"
    pattern_type: str = "task"  # "task" or "behavioral"

    def merge(self, other: "Pattern") -> "Pattern":
        """Merge another pattern into this one (combines frequencies, signals)."""
        # If either is behavioral, the merged pattern stays behavioral
        merged_type = (
            "behavioral"
            if "behavioral" in (self.pattern_type, other.pattern_type)
            else "task"
        )
        return Pattern(
            pattern_name=self.pattern_name,
            description=self.description
            if self.frequency >= other.frequency
            else other.description,
            frequency=self.frequency + other.frequency,
            trigger_signals=list(
                dict.fromkeys(self.trigger_signals + other.trigger_signals)
            ),
            trigger_context_hints=list(
                dict.fromkeys(self.trigger_context_hints + other.trigger_context_hints)
            ),
            typical_flow=self.typical_flow
            if len(self.typical_flow) >= len(other.typical_flow)
            else other.typical_flow,
            user_preferences={**self.user_preferences, **other.user_preferences},
            complexity="dynamic"
            if "dynamic" in (self.complexity, other.complexity)
            else "static",
            pattern_type=merged_type,
        )


def _parse_patterns_json(text: str) -> list[dict]:
    """Parse LLM response text into a list of pattern dicts."""
    text = text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "patterns" in result:
            return result["patterns"]
        return [result]
    except json.JSONDecodeError:
        return []


def _signal_overlap(a: list[str], b: list[str]) -> float:
    """Compute Jaccard similarity between two trigger signal lists."""
    set_a = {s.lower() for s in a}
    set_b = {s.lower() for s in b}
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


async def extract_patterns(
    sessions: list[dict],
    user_id: str,
    client: genai.Client,
    model: str = cfg.ANALYSIS_MODEL,
    min_frequency: int = 3,
    batch_size: int = 10,
) -> list[Pattern]:
    """Analyze sessions and extract recurring intent patterns.

    Args:
        sessions: List of session dicts loaded from history/{user_id}/*.json.
        user_id: The user being analyzed.
        client: Google Cloud genai client.
        model: Model for analysis.
        min_frequency: Minimum session count to keep a pattern.
        batch_size: Number of sessions per LLM batch.

    Returns:
        List of Pattern objects, sorted by frequency descending.
    """
    # Batch sessions
    batches = [
        sessions[i : i + batch_size] for i in range(0, len(sessions), batch_size)
    ]

    all_raw_patterns: list[dict] = []

    for batch_idx, batch in enumerate(batches):
        # Prepare sessions for the prompt (strip large metadata to fit context)
        slim_sessions = []
        for s in batch:
            slim_sessions.append(
                {
                    "scenario_id": s.get("scenario_id", ""),
                    "intent": s.get("intent", ""),
                    "follow_up_strategy": s.get("follow_up_strategy", ""),
                    "turns": s.get("turns", []),
                    "turn_count": s.get("turn_count", 0),
                }
            )

        prompt = _EXTRACTION_PROMPT.format(
            batch_size=len(batch),
            user_id=user_id,
            sessions_json=json.dumps(slim_sessions, indent=1, ensure_ascii=False),
        )

        from analyzer.llm_util import generate_with_fallback

        response = await generate_with_fallback(
            client=client,
            model=model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        raw_patterns = _parse_patterns_json(response.text)
        all_raw_patterns.extend(raw_patterns)

    # Convert to Pattern objects
    patterns_by_name: dict[str, Pattern] = {}

    for raw in all_raw_patterns:
        name = raw.get("pattern_name", "unknown")
        # Support both old field name (trigger_signals) and new (trigger_keywords)
        keywords = raw.get("trigger_keywords") or raw.get("trigger_signals", [])
        context_hints = raw.get("trigger_context_hints", [])
        pattern = Pattern(
            pattern_name=name,
            description=raw.get("description", ""),
            frequency=raw.get("frequency", 1),
            trigger_signals=keywords,
            trigger_context_hints=context_hints,
            typical_flow=raw.get("typical_flow", []),
            user_preferences=raw.get("user_preferences", {}),
            complexity=raw.get("complexity", "static"),
            pattern_type=raw.get("pattern_type", "task"),
        )

        if name in patterns_by_name:
            patterns_by_name[name] = patterns_by_name[name].merge(pattern)
        else:
            patterns_by_name[name] = pattern

    # Merge patterns with high signal overlap but different names
    merged = list(patterns_by_name.values())
    to_remove = set()
    for i in range(len(merged)):
        if i in to_remove:
            continue
        for j in range(i + 1, len(merged)):
            if j in to_remove:
                continue
            if (
                _signal_overlap(merged[i].trigger_signals, merged[j].trigger_signals)
                > 0.5
            ):
                # Merge j into i (keep the higher-frequency one)
                if merged[i].frequency >= merged[j].frequency:
                    merged[i] = merged[i].merge(merged[j])
                    to_remove.add(j)
                else:
                    merged[j] = merged[j].merge(merged[i])
                    to_remove.add(i)
                    break

    final = [p for idx, p in enumerate(merged) if idx not in to_remove]

    # Filter by min frequency
    final = [p for p in final if p.frequency >= min_frequency]

    # Sort by frequency descending
    final.sort(key=lambda p: p.frequency, reverse=True)

    return final
