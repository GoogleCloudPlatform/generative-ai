# Test Scenarios — User Assistant Agent

5 realistic multi-turn conversations covering different capabilities: factual Q&A, web search, disambiguation, multilingual support, and correction handling.

---

## Scenario 1: Follow-up clarification — geography deep-dive

**Capability tested:** Multi-turn factual Q&A with progressive depth
**Expected tools:** None (general knowledge)

**Turn 1 — User:**
> What's the tallest mountain in the world?

**Expected agent behaviour:**
- Answer: Mount Everest
- Brief context (location, height)

**Turn 2 — User:**
> How tall is it exactly?

**Expected agent behaviour:**
- Provide the height (8,849 metres / 29,032 feet)
- Not repeat the full introduction from Turn 1

**Turn 3 — User:**
> Has anyone died trying to climb it?

**Expected agent behaviour:**
- Provide factual information about fatalities on Everest
- May use web search for current statistics
- Appropriate tone for a sensitive topic

---

## Scenario 2: Current events — web search required

**Capability tested:** Web search for current information, source citation
**Expected tools:** google_search

**Turn 1 — User:**
> What is the James Webb Space Telescope?

**Expected agent behaviour:**
- Explain JWST from general knowledge (NASA, infrared, successor to Hubble)
- May or may not use web search (general knowledge is sufficient)

**Turn 2 — User:**
> What are some of its most important discoveries so far?

**Expected agent behaviour:**
- Use web search to find recent discoveries
- Cite sources for specific findings
- Well-structured list of key discoveries

---

## Scenario 3: Multi-topic conversation — topic switching

**Capability tested:** Handling unrelated topics in one session
**Expected tools:** None required

**Turn 1 — User:**
> What's a good recipe for pancakes?

**Expected agent behaviour:**
- Provide a clear, practical recipe
- Include ingredients and basic steps

**Turn 2 — User:**
> Thanks! Completely different topic — can you explain what blockchain is in simple terms?

**Expected agent behaviour:**
- Switch topics cleanly without confusion
- Explain blockchain in accessible language
- Not reference pancakes or try to connect the topics

---

## Scenario 4: Multilingual — Mandarin conversation

**Capability tested:** Responding in the user's language
**Expected tools:** None required

**Turn 1 — User:**
> 你好，请问澳大利亚的首都是哪里？

*(Translation: "Hello, what is the capital of Australia?")*

**Expected agent behaviour:**
- Respond in Mandarin
- Answer: 堪培拉 (Canberra)
- May add brief context

**Turn 2 — User:**
> 谢谢！悉尼为什么不是首都？

*(Translation: "Thanks! Why isn't Sydney the capital?")*

**Expected agent behaviour:**
- Respond in Mandarin
- Explain the historical compromise between Sydney and Melbourne
- Clear and informative

---

## Scenario 5: Correction handling — user redirects

**Capability tested:** Gracefully handling user corrections
**Expected tools:** None required

**Turn 1 — User:**
> Who wrote Romeo and Juliet?

**Expected agent behaviour:**
- Answer: William Shakespeare

**Turn 2 — User:**
> Actually I meant the movie, not the play. Who directed the 1996 film version?

**Expected agent behaviour:**
- Acknowledge the clarification gracefully (not defensively)
- Answer: Baz Luhrmann
- May add brief context about the film

---

## How to run these tests

```bash
# Start the agent locally
adk web --port 8000
```

## Evaluation criteria

For each scenario, check:

| Criteria | Pass condition |
|---|---|
| **Accuracy** | Agent provides factually correct information |
| **Helpfulness** | Response directly addresses the user's question |
| **Source usage** | Web search used when current info is needed, sources cited |
| **Clarity** | Well-structured and easy to understand |
| **Conciseness** | Appropriate length — thorough but not verbose |
| **Tone** | Friendly, natural, not robotic |
| **Multilingual** | Responds in the user's language when applicable |
