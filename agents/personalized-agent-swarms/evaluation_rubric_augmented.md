# Evaluation Rubric — Augmented Assistant Agent (Baseline + Swarm Dimensions)

Use this rubric to score the augmented assistant from the perspective of a **returning user who has established preferences and recurring tasks**. The augmented agent should demonstrate personalized intelligence beyond generic responses.

This rubric includes all 8 baseline dimensions plus 2 swarm-specific dimensions.

---

## Scoring Scale

| Score | Label | Meaning |
|-------|-------|---------|
| 1 | Poor | Actively unhelpful — wrong answer, fabricated information, or confusing |
| 2 | Below expectations | Partially correct but missing key info or hard to follow |
| 3 | Meets expectations | Correct answer, clear enough to act on, appropriate tone |
| 4 | Exceeds expectations | Correct, well-structured, proactively useful, personalized |

---

## Baseline Dimensions (1-8)

### 1. Accuracy (weight: critical)
Same as baseline rubric. Any fabrication caps overall score at 1.

### 2. Helpfulness (weight: high)
Same as baseline rubric.

### 3. Source Usage (weight: high)
Same as baseline rubric.

### 4. Clarity (weight: medium)
Same as baseline rubric.

### 5. Conciseness (weight: medium)
Same as baseline rubric.

### 6. Tone (weight: medium)
Same as baseline rubric.

### 7. Multi-Part Handling (weight: medium, N/A if single question)
Same as baseline rubric.

### 8. Multilingual Support (weight: medium, N/A if English)
Same as baseline rubric.

---

## Swarm-Specific Dimensions (9-10)

### 9. Personalization (weight: high)

> _"Does this response feel like it was written for ME, or for a generic user?"_

Combines proactive intelligence (anticipating needs without being asked) with
preference alignment (matching format, tone, detail level).

| Score | Criteria |
|-------|----------|
| 1 | Ignores known preferences AND misses obvious follow-up needs |
| 2 | Partially aligned — generic response that could be for any user |
| 3 | Matches most preferences OR includes proactive elements |
| 4 | Perfectly aligned with preferences AND anticipated the user's full workflow |

**Examples:**
- Score 1: User prefers code examples and always needs edge cases, agent gives prose-only explanation of the happy path
- Score 4: User prefers terse code with inline comments, agent delivers exactly that plus edge cases and defensive tips — all without being asked

---

### 10. Turn Efficiency (weight: medium)

> _"Did I get what I needed in fewer back-and-forths?"_

| Score | Criteria |
|-------|----------|
| 1 | Required MORE turns than baseline to reach the same outcome |
| 2 | Same number of turns as baseline |
| 3 | One fewer turn than baseline |
| 4 | Two or more fewer turns than baseline while maintaining quality |

---

## How to Calculate the Overall Score

1. **Accuracy gate:** If the agent fabricates key facts, overall score = **1**.
2. **Weighted average:** Compute across all applicable dimensions (skip N/A).
3. **Round** to nearest 0.5.

---

## LLM Judge Prompt Template

```
You are evaluating an AI assistant augmented with personalized mini-agents.
You are judging from the perspective of a returning user with known
preferences and recurring task patterns.

The user's known preferences are provided below. Use them to evaluate
preference alignment and proactive intelligence.

Score every applicable dimension on a 1-4 scale. Return a JSON object:
- "scores": object with keys: accuracy, helpfulness, source_usage, clarity,
  conciseness, tone, multi_part_handling, multilingual_support,
  personalization, turn_efficiency.
  Each value is an integer 1-4, or null if N/A.
- "justifications": same keys, one-sentence justification or null.
- "overall_score": float rounded to nearest 0.5.

Accuracy rule: fabricated facts/sources -> overall_score = 1.0.

<user_preferences>
{user preferences from swarm metadata}
</user_preferences>

<baseline_turns>
{number of turns the baseline agent needed}
</baseline_turns>

<rubric>
{paste dimensions above}
</rubric>

<conversation>
{the augmented agent conversation to evaluate}
</conversation>
```
