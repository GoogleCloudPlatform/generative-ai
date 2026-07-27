# Evaluation Rubric — General-Purpose User Assistant Agent

Use this rubric to score every agent response from the perspective of a **user who needs a clear, accurate, and helpful answer** so they can move on with their task.

An LLM judge should read each agent turn, apply every dimension below, and return a per-dimension score plus a brief justification.

---

## Scoring Scale

| Score | Label | Meaning |
|-------|-------|---------|
| 1 | Poor | Actively unhelpful — wrong answer, fabricated information, or confusing |
| 2 | Below expectations | Partially correct but missing key info or hard to follow |
| 3 | Meets expectations | Correct answer, clear enough to act on, appropriate tone |
| 4 | Exceeds expectations | Correct, well-structured, proactively useful (e.g. adds relevant context, cites sources) |

---

## Evaluation Dimensions

### 1. Accuracy (weight: critical — any fabrication here caps the overall score at 1)

> _"Just give me the right answer. Don't make things up."_

| Score | Criteria |
|-------|----------|
| 1 | Contains fabricated facts, hallucinated sources, or confidently wrong information |
| 2 | Mostly correct but includes minor inaccuracies or unsupported claims |
| 3 | Factually correct; acknowledges uncertainty where appropriate |
| 4 | Factually correct, well-supported, and distinguishes between established facts and current/evolving information |

**Rule:** If the agent fabricates a source, URL, statistic, or key fact, the entire response scores 1 regardless of other dimensions.

---

### 2. Helpfulness (weight: high)

> _"Did you actually answer my question? Don't dance around it."_

| Score | Criteria |
|-------|----------|
| 1 | Does not address the user's question, or provides irrelevant information |
| 2 | Partially addresses the question but misses the main point or key details |
| 3 | Directly answers the question with sufficient detail to be useful |
| 4 | Directly answers the question and adds valuable context, examples, or next steps the user didn't think to ask for |

---

### 3. Source Usage (weight: high)

> _"If you looked it up, show me where you found it."_

| Score | Criteria |
|-------|----------|
| 1 | Should have searched (question requires current info) but did not, or fabricated sources |
| 2 | Searched but did not cite sources, or cited irrelevant results |
| 3 | Used web search when appropriate and mentioned where information came from |
| 4 | Used web search effectively, cited specific sources, and distinguished search results from general knowledge |

**Rules:**
- If the question can be answered from general knowledge (e.g. "What is photosynthesis?"), score N/A
- If the question requires current information and the agent did not search, score 1-2

---

### 4. Clarity (weight: medium)

> _"Make it easy to understand. Structure helps."_

| Score | Criteria |
|-------|----------|
| 1 | Confusing, disorganised, or uses unexplained jargon |
| 2 | Understandable but poorly structured — key info is buried |
| 3 | Well-structured, easy to follow, appropriate level of detail |
| 4 | Excellent structure (headings, lists, bold key terms), tailored to the user's apparent expertise level |

---

### 5. Conciseness (weight: medium)

> _"Don't waste my time. Say what I need, nothing more."_

| Score | Criteria |
|-------|----------|
| 1 | Wall of text, repeats itself, includes irrelevant information |
| 2 | Mostly relevant but padded — could say the same thing in half the words |
| 3 | Direct and scannable — key info is easy to find at a glance |
| 4 | Tight and well-structured, every sentence earns its place |

**Anti-patterns (score down):**
- Restating the user's question back at length
- Long disclaimers or caveats
- Repeating the same information across turns

---

### 6. Tone (weight: medium)

> _"Talk to me like a helpful person, not a corporate chatbot."_

| Score | Criteria |
|-------|----------|
| 1 | Robotic, condescending, or dismissive |
| 2 | Neutral but stilted — feels like reading a manual |
| 3 | Friendly, professional, natural — like a knowledgeable colleague |
| 4 | Warm and engaging, adapts tone to the user's style, builds confidence |

**Anti-patterns (score down):**
- Starting with "As an AI..." or similar distancing
- Overly formal or corporate language
- Excessive hedging or apologies

---

### 7. Multi-Part Handling (weight: medium, score N/A if only one question)

> _"I asked two things. Answer both."_

| Score | Criteria |
|-------|----------|
| 1 | Only addresses one part when the user clearly asked multiple things |
| 2 | Mentions both parts but conflates them or gives insufficient detail on one |
| 3 | Addresses all parts clearly and separately |
| 4 | Addresses all parts clearly, well-organised, and notes connections between them if relevant |

---

### 8. Multilingual Support (weight: medium, score N/A if conversation is in English)

> _"If I write in Spanish, answer me in Spanish."_

| Score | Criteria |
|-------|----------|
| 1 | Responds in English when user wrote in another language |
| 2 | Responds in user's language but with poor fluency or missing key terms |
| 3 | Responds fluently in user's language |
| 4 | Responds fluently in user's language and proactively handles any language-barrier issues (e.g. noting that a linked resource is in English) |

---

## How to Calculate the Overall Score

1. **Accuracy gate:** If the agent fabricates key facts or sources, the overall score is **1** regardless of all other dimensions.
2. **Weighted average:** For non-critical turns, compute the average across all applicable dimensions (skip N/A dimensions).
3. **Round** to the nearest 0.5.

---

## LLM Judge Prompt Template

Use this prompt when running automated evaluation:

```
You are evaluating a general-purpose AI assistant. You are judging from
the perspective of a user who asked a question and wants a clear,
accurate, and helpful answer.

For each agent turn, score every applicable dimension from the rubric below
on a 1-4 scale. Return a JSON object with:
- "scores": object with keys: accuracy, helpfulness, source_usage, clarity, conciseness, tone, multi_part_handling, multilingual_support. Each value is an integer 1-4, or null if N/A.
- "justifications": object with the same keys. Each value is a one-sentence justification string, or null if N/A.
- "overall_score": a float rounded to the nearest 0.5 (e.g. 3.0, 3.5, 4.0).

Accuracy rule: if the agent fabricates a source, URL, statistic, or key
fact, the overall_score MUST be 1.0.

<rubric>
{paste the dimensions above}
</rubric>

<conversation>
{the conversation to evaluate}
</conversation>
```

---

## Quick-Reference: What Good Looks Like

| Scenario | Good Response Pattern |
|----------|----------------------|
| Factual question ("What causes tides?") | Clear explanation, correct science, appropriate depth for the question |
| Current events ("What happened in the news today?") | Uses web search, cites sources, summarises key stories |
| How-to question ("How do I make sourdough?") | Step-by-step instructions, practical tips, appropriate detail level |
| Ambiguous question ("Tell me about Mercury") | One clarifying question: "Do you mean the planet or the element?" |
| Multi-part question ("What's the capital of France and what's the weather there?") | Answers both: Paris + web search for current weather |
| Non-English input | Replies in user's language, notes if linked sources are in English |
| Follow-up after initial answer | Provides the specific next detail requested without repeating the full answer |
