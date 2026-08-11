# Personalized Mini-Agent Swarms from Conversational History

An end-to-end system that analyzes a user's past conversations with an AI assistant, identifies recurring intent patterns, and automatically generates specialized **mini-agents** that activate at runtime — reducing the number of prompts needed and improving output quality through learned preferences.

Built on [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) with Google Cloud and Gemini models.

**Authors:** [Tanya Dixit](https://github.com/tanyagoogle) (`@tanyagoogle`), [Pouya Omran](https://github.com/PouyaOmran) (`@PouyaOmran`), [Soujanya Lanka](https://github.com/soujanyav) (`@soujanyav`), [Qin Zhang](https://github.com/olifei) (`@olifei`)

> [!NOTE]
> This is an **experimental research pipeline** shared as a sample, not a
> production-ready product. It demonstrates an approach to runtime agent
> personalization and is intended for learning and experimentation. Set your
> own Google Cloud project and model configuration via `.env` (see `.env.example`)
> before running.

---

## Table of Contents

- [Core Idea](#core-idea)
- [Architecture](#architecture)
- [Pipeline Phases](#pipeline-phases)
  - [Phase 1: History Harvest](#phase-1-history-harvest)
  - [Phase 2: Pattern Analysis & Swarm Generation](#phase-2-pattern-analysis--swarm-generation)
  - [Phase 3: Augmented Assistant Agent](#phase-3-augmented-assistant-agent)
  - [Phase 4: Comparative Evaluation](#phase-4-comparative-evaluation)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Running the Pipeline](#running-the-pipeline)
- [Evaluation Methodology](#evaluation-methodology)
- [Evaluation Results](#evaluation-results)
- [Key Design Decisions](#key-design-decisions)
- [Limitations & Future Work](#limitations--future-work)

---

## Core Idea

Generic AI assistants treat every user the same. A software engineer debugging Python and a marketing manager writing campaign copy both get the same generic responses — requiring multiple follow-up turns to reach the desired output format, detail level, and scope.

This project addresses that by:

1. **Observing** — harvesting multi-turn conversations between simulated users and a baseline assistant
2. **Learning** — using LLM-based analysis to extract recurring intent patterns and user preferences
3. **Generating** — producing specialized mini-agents (Python modules) with baked-in preferences
4. **Activating** — loading the right mini-agent at runtime via embedding-based semantic matching

The result: an augmented assistant that delivers a complete, preference-aligned response in **fewer turns**.

```
                    Baseline                          Augmented
               +-----------------+            +---------------------+
    Turn 1     | User: "I have   |            | User: "I have a     |
               | a KeyError..."  |            | KeyError..."        |
               | Asst: "That     |            |                     |
               | usually means..."|            | [swarm triggers     |
    Turn 2     | User: "Here's   |            |  deep_dive_debugging|
               | the traceback"  |            |  mini-agent]        |
               | Asst: "The col  |            |                     |
               | type mismatch"  |            | Asst: diagnosis +   |
    Turn 3     | User: "Edge     |            | fix + edge cases +  |
               | cases?"         |            | defensive tips      |
               | Asst: "Watch    |            | (all in ONE turn)   |
               | for NaN..."     |            +---------------------+
               +-----------------+
                    3 turns                          1 turn
```

---

## Architecture

```
+----------------------------------------------------------------------+
|                         PIPELINE OVERVIEW                             |
|                                                                       |
|  +-----------+    +-----------+    +-----------+    +-----------+     |
|  |  HARVEST   |--->|  ANALYZE  |--->|  AUGMENT  |--->| EVALUATE  |    |
|  |  Phase 1   |    |  Phase 2  |    |  Phase 3  |    |  Phase 4  |    |
|  +-----------+    +-----------+    +-----------+    +-----------+     |
|       |                |                |                |            |
|       v                v                v                v            |
|  +---------+    +-----------+    +-----------+    +----------+       |
|  |history/  |    | swarms/   |    | augmented |    |evaluation|       |
|  | user_N/  |    |  user_N/  |    | _assistant|    | _output/ |       |
|  | sessions |    |  agents/  |    | _agent/   |    |  reports |       |
|  +---------+    |  triggers |    +-----------+    +----------+       |
|                  |  embeds   |                                        |
|                  +-----------+                                        |
+----------------------------------------------------------------------+
```

### Runtime Architecture (Phase 3)

```
+----------------------------------------------------------+
|                    User Message                           |
|            "Getting a TypeError in my..."                 |
+-------------------------+--------------------------------+
                          |
                          v
+----------------------------------------------------------+
|              Augmented Assistant Agent                     |
|                 (ADK / Gemini 3 Flash Preview)             |
|                                                           |
|   Tools: [check_and_invoke_swarm]                         |
|                                                           |
|   1. Calls check_and_invoke_swarm(user_message)           |
|                       |                                   |
|                       v                                   |
|   +----------------------------------------------+       |
|   |          Active Memory (active_mem)            |       |
|   |                                                |       |
|   |  a. load_swarm(user_id)                        |       |
|   |     +-> swarms/user_N/triggers.json            |       |
|   |     +-> swarms/user_N/agents/*.py              |       |
|   |                                                |       |
|   |  b. Extract features (1 Flash call, shared)    |       |
|   |     +-> domain, task_type, specificity,        |       |
|   |         topic_keywords, action_object           |       |
|   |                                                |       |
|   |  c. Soft attribute filter: domain/task_type    |       |
|   |     mismatches apply penalties (not hard reject) |       |
|   |                                                |       |
|   |  d. Semantic ranking: embed user message       |       |
|   |     (text-embedding-005) + cosine similarity   |       |
|   |     against pre-computed agent scope embeddings |       |
|   |                                                |       |
|   |  e. Stage 2: Binary questionnaire               |       |
|   |     disambiguation (parallel Flash calls)       |       |
|   |     40% embedding + 60% questionnaire score     |       |
|   |                                                |       |
|   |  f. If still ambiguous: Pro LLM tiebreaker     |       |
|   |                                                |       |
|   |  g. If matched: execute mini-agent              |       |
|   |     +-> multi-step LLM pipeline                |       |
|   |     +-> return enriched response                |       |
|   +----------------------------------------------+       |
|                       |                                   |
|                       v                                   |
|   2. Return response (auto / suggest / none)              |
|                                                           |
|   auto --> deliver mini-agent response directly           |
|   suggest --> standard response + offer mini-agent        |
|   none --> respond with standard capabilities             |
+----------------------------------------------------------+
```

---

## Pipeline Phases

### Phase 1: History Harvest

**Goal:** Generate realistic conversational history by simulating multi-turn conversations between user personas and a baseline assistant.

**Components:**
- `user_profiles/profiles.json` — 5 user personas with 50 scenarios each (250 total)
- `harvest/user_agent.py` — Gemini-powered agent that role-plays a user persona
- `harvest/orchestrator.py` — Drives the conversation loop, saves session logs

**User Personas:**

| User | Persona | Recurring Intents |
|------|---------|-------------------|
| `user_1` | Software engineer (Python, Google Cloud) | Debug code, write tests, deploy services, review PRs, optimize SQL, write Dockerfiles, configure CI/CD |
| `user_2` | Marketing manager | Write copy, analyze metrics, plan campaigns, create presentations |
| `user_3` | ML graduate student | Explain papers, summarize concepts, help with LaTeX, find datasets |
| `user_4` | Small business owner | Financial planning, legal questions, hiring, inventory |
| `user_5` | Travel enthusiast + home cook | Plan trips, find recipes, compare products, learn languages |

**How it works:**

```
For each user (5) x each scenario (50):
  1. User agent generates opening message (from scenario)
  2. Baseline assistant responds
  3. User agent generates follow-up (based on strategy: clarify/deep_dive/pivot/correct)
  4. Repeat for 2-5 turns
  5. Save full conversation to history/{user_id}/session_{NNN}.json
```

**Session JSON format:**
```json
{
  "user_id": "user_1",
  "scenario_id": "scenario_001",
  "intent": "debug_python_code",
  "follow_up_strategy": "deep_dive",
  "turns": [
    {"role": "user", "content": "Getting a TypeError..."},
    {"role": "assistant", "content": "That usually happens when..."},
    {"role": "user", "content": "What about edge cases?"},
    {"role": "assistant", "content": "Watch for NaN values..."}
  ],
  "turn_count": 2,
  "metadata": {"persona": "...", "max_turns": 3}
}
```

### Phase 2: Pattern Analysis & Swarm Generation

**Goal:** Analyze each user's conversation history, extract recurring intent patterns, and generate a swarm of specialized mini-agents with pre-computed scope embeddings.

**Components:**
- `analyzer/pattern_extractor.py` — LLM-based pattern extraction (Gemini 3.1 Pro)
- `analyzer/swarm_generator.py` — Generates mini-agent Python modules + triggers + embeddings (Gemini 3.1 Pro)
- `analyzer/trigger_schema.py` — Shared feature schema, extraction prompts, matching logic, and rule validation
- `analyzer/analyze_history.py` — Main entry point

**Pattern extraction process:**

```
50 sessions --> batch into groups of 10
                    |
                    v
            LLM analyzes each batch:
            - Identify recurring intents
            - Classify as "task" or "behavioral" pattern
            - Extract trigger signals (keywords, phrases)
            - Map typical conversation flow
            - Capture user preferences (format, detail, tone)
                    |
                    v
            Merge across batches, deduplicate
                    |
                    v
            Filter: keep patterns with frequency >= 3
                    |
                    v
            Separate task vs behavioral patterns
                    |
            +-------+-------+
            v               v
    Task patterns     Behavioral patterns
    (what user wants) (how user communicates)
            |               |
            v               v
    Generate per       Synthesize into
    pattern:           user_style.json
    +-- triggers.json  (response_length,
    +-- agents/*.py    tone, format, etc.)
    +-- scope embeds        |
                    +-------+
                    v
            Critic/Revision Pass (optional):
            1. Compile-check each agent
            2. Run execute() against matching history session
            3. Compare output vs gold reference from history
            4. LLM critic rewrites agents that fail
            5. Update triggers if misaligned
                    |
                    v
            Compute Scope Embeddings:
            text-embedding-005 embeds each agent's
            description + trigger signals + typical flow
            into 768-dim vectors stored in triggers.json
                    |
                    v
            Coverage Validation (post-ranking):
            1. Check if dropped agents' patterns are
               covered by surviving agents
            2. Widen closest surviving agent to absorb
               orphaned patterns (domain expansion,
               exclusion removal)
            3. Expand broadest agent's domains for
               cross-domain users (inferred from persona)
            4. Recompute embeddings if gaps were resolved
```

**Generated mini-agent structure:**

Each mini-agent is a standalone Python module with:

```python
AGENT_META = {
    "name": "deep_dive_debugging",
    "description": "...",
    "complexity": "dynamic",    # "static" (single prompt) or "dynamic" (multi-step)
    "source_sessions": 6,       # how many sessions informed this agent
}

STEPS = [                       # for dynamic agents (max 2 steps)
    {"name": "diagnose", "prompt": "...{user_message}..."},
    {"name": "fix", "prompt": "...{previous_output}..."},
]

async def execute(user_message: str, llm_client) -> str:
    # Runs each step sequentially, feeding output forward
```

**Behavioral vs task pattern separation:**

Patterns are classified as either **task** (what the user wants done — e.g., "cafe financial planning") or **behavioral** (how the user communicates — e.g., "sends incomplete messages when overwhelmed"). Behavioral patterns are aggregated into a `user_style.json` profile instead of becoming standalone agents, preventing false positive triggers on communication style rather than intent.

**Trigger types:**

| Type | Mechanism | Cost | Use Case |
|------|-----------|------|----------|
| `attribute_match` | Feature extraction (1 Flash call) + soft attribute penalties + embedding cosine similarity ranking + binary questionnaire disambiguation | 1 Flash + 1 embedding call (shared) + 1 Flash per candidate (Stage 2) | **Default** — two-stage matching. Stage 1: embedding similarity with soft domain/task_type penalties (0.15/0.10). Stage 2: per-agent binary questionnaires (3-5 yes/no questions) evaluated in parallel. Combined score: 40% embedding + 60% questionnaire. Pro LLM fallback only when questionnaires are inconclusive |
| `llm_match` | Two-stage LLM matching: parallel Flash screening + Pro tiebreak | 1-N+1 LLM calls | Legacy fallback — skipped when all agents have scope embeddings |
| `keyword_and_context` | Substring matching against keyword + context hint lists | Zero (no LLM call) | Legacy — skipped when embeddings available |
| `intent_classification` | LLM classifies user intent against phrase list | One LLM call | Legacy — skipped when embeddings available |

**Matching pipeline:** When all agents have scope embeddings (default), only `attribute_match` runs — legacy fallback stages (`llm_match`, `keyword_and_context`, `intent_classification`) are skipped entirely. The two-stage pipeline (embedding filter + binary questionnaires) provides both broad recall and precise disambiguation without keyword-related false positives.

**Critic/revision pass:**

An optional post-generation validation that runs each agent against actual conversation history to verify output quality:

1. **Code validity** — `compile()` each agent, verify `execute()` is async
2. **Output quality** — Run `execute(first_user_turn)` from a matching session, send output + gold reference to a critic LLM (scoring on a 0-10 scale across 7 dimensions: COMPLETENESS, STYLE ALIGNMENT, ANTI-PATTERN AVOIDANCE, CONTENT QUALITY, TRUNCATION, TRIGGER FIT, HALLUCINATION)
3. **Fabrication hard-ceiling** — If the critic detects >= 2 factual contradictions (fabricated API names, CLI flags, URLs, function signatures), the agent score is capped at 4/10 regardless of other criteria
4. **Trigger quality** — Critic also validates trigger descriptions against test messages
5. **Multi-round revision** — If the critic fails an agent (score < 7/10), a separate revise-only LLM call generates revised code based on the specific issues identified. Up to 3 rounds; exits early if no score improvement. The evaluate and revise steps use separate LLM calls to prevent scoring bias
6. **Non-parametric quality ranking** — After the critic pass, all agents are evaluated holistically by an LLM (Gemini 3.1 Pro) using a 5-dimension rubric (VALUE×3, DISTINCTIVENESS×2, TRIGGER_CLARITY×2, QUALITY×2, FREQUENCY×1; max 50). There is no fixed target count — every agent scoring >= 25/50 is kept. The LLM can veto redundant or low-value agents. Hard safety cap of 30 agents applies before generation as a cost guardrail. Falls back to frequency-based filtering (>= 4 sessions) on LLM failure

**Validation gate (V8 — mini-eval harness):**

After ranking, each surviving agent is validated using the **same multi-turn evaluation harness** used in Phase 4. This ensures validation quality is representative of actual final evaluation:

1. **Scenario seeding** — From 50 pre-computed historic sessions, pick top 3 similar (by embedding match) + 3 different scenarios per agent. Similar scenarios include the gold reference response from history for goal evaluation.
2. **Multi-turn conversation** — For each similar scenario, run the augmented agent (with only this agent's swarm) through a simulated user conversation (up to 3 turns) using the same `run_eval_user_turn` function from the eval harness.
3. **3-dimension judge** — Each conversation is scored by the same LLM judge used in final evaluation (accuracy, helpfulness, personalization on 1-4 scale).
4. **Pruning criteria** — `avg_accuracy < 2.5` (remove), `trigger_rate == 0` (remove), `false_positive_count > 1` (remove), any scenario with fabrication detected (flag for removal).

**Parallel generation with best-pick (V8):**

Each agent is generated in two parallel LLM calls at different temperatures (0.2 and 0.35). Both candidates are compile-checked. If both compile, a Flash LLM selects the more grounded and accurate one. This reduces fabrication by providing diversity in generation and selecting the safer option.

**Post-generation fact-check (V8):**

Before writing each agent to disk, a Flash LLM scans the ENRICHED_PROMPT for specific claims (API names, CLI flags, URLs, technical details) and rates each as HIGH/MEDIUM/LOW confidence. LOW-confidence claims are revised to include uncertainty caveats ("verify the exact flag name") rather than stated as fact.

### Phase 3: Augmented Assistant Agent

**Goal:** An ADK agent that wraps the baseline assistant with an active memory layer, loading user-specific swarms at runtime.

**Components:**
- `augmented_assistant_agent/agent.py` — ADK agent definition with two tools: `check_and_invoke_swarm` + `baseline_assistant` (AgentTool)
- `augmented_assistant_agent/tools/active_mem.py` — Trigger matching + mini-agent invocation + hallucination detection
- `augmented_assistant_agent/tools/swarm_loader.py` — Dynamic Python module loading

**Architecture:** The augmented agent uses an `AgentTool`-wrapped baseline sub-agent. When `check_and_invoke_swarm` returns `action="none"` (no swarm match), the augmented agent delegates to `baseline_assistant` — an `AgentTool` wrapping an `Agent` with instructions identical to `user_assistant_agent`. This ensures baseline-equivalent behavior on the no-swarm path.

**Two-stage trigger matching (V8):**

1. **Stage 1 — Embedding + attribute filter:** Extract features (1 Flash call) + embed user message (text-embedding-005). Score all agents with soft attribute penalties + cosine similarity. All agents above threshold pass.
2. **Stage 2 — Binary questionnaire disambiguation:** Each agent has 3-5 contrastive yes/no questions generated at swarm creation time. For all passing agents, evaluate their questionnaires in parallel (1 Flash call each). Combine scores: 40% embedding + 60% questionnaire match ratio. If one agent passes with >= 0.8 match ratio, select it. If multiple pass, pick highest combined score. If none pass, escalate to Pro LLM tiebreaker with conversation history.

**Three response modes:**

| Mode | When | Behavior |
|------|------|----------|
| **Auto** | Trigger matches with high confidence | Mini-agent runs silently; its output is returned as the assistant's response |
| **Suggest** | Trigger matches but lower confidence | Standard response + "I can also [X] -- would you like me to?" |
| **None** | No trigger matches | Delegates to `baseline_assistant` (AgentTool) for standard behavior |

**Task-adaptive style dampening:**

When a user message signals a complex task (financial plan, pricing strategy, multi-part analysis), style constraints that would force fragmentation ("bite-sized", "one concept at a time") are surgically removed from the relevant style keys while preserving non-conflicting preferences. This prevents multi-turn loops where the agent asks for permission to continue instead of delivering the full answer.

### Phase 4: Comparative Evaluation

**Goal:** Quantify the improvement from personalized swarms by running identical scenarios through both agents using a **user-agent-driven** approach.

**Components:**
- `test_augmented_agent.py` — User-agent-driven evaluation with scenario sampling
- `evaluation_rubric_augmented.md` — 10-dimension scoring rubric
- LLM-as-judge evaluation via Gemini 3.1 Pro (fallback: 2.5 Pro)

**How it works:**

A simulated user agent drives **both** conversations with the **same opening message** (sampled from `profiles.json`). The user agent decides autonomously when to continue asking follow-ups and when the goal is reached (via a `[GOAL_REACHED]` signal). Both agents get identical input — the only difference is whether a personalized swarm fires. A max-turn cap prevents runaway conversations.

```
                    Same opening message
                   +--------------------+
                   |                    |
            +------v------+     +------v------+
            |  Baseline   |     |  Augmented   |
            |  Assistant  |     |  Assistant   |
            +------+------+     +------+------+
                   |                    |
            +------v------+     +------v------+
            | User agent  |     | User agent  |
            | continues   |     | says        |
            | follow-ups  |     | GOAL_REACHED|
            +------+------+     +-------------+
                   |
            More turns...         Fewer turns!
```

**What is measured:**
1. **Turn count** — How many turns each agent needed before the user agent's goal was reached
2. **Goal reached** — Whether the user agent explicitly signaled `[GOAL_REACHED]` vs hitting the max-turn cap
3. **Quality scoring** — LLM judge rates both agents on 10 dimensions (1-4 scale) and declares a winner
4. **Split analysis** — Results are reported separately for similar (should trigger) vs different (should not trigger) scenarios

---

## Project Structure

```
ADK_agents/
+-- user_assistant_agent/              # Baseline agent (unchanged)
|   +-- __init__.py
|   +-- agent.py                       # ADK Agent: Gemini 3 Flash Preview (no tools)
|   +-- .env                           # Google Cloud config
|   +-- requirements.txt
|   +-- README.md
|   +-- DEPLOYMENT.md                  # Cloud deployment guide
|   +-- test_scenarios.md              # Manual test case definitions
|
+-- harvest/                           # Phase 1: History generation
|   +-- orchestrator.py                # Drives user<->assistant conversations
|   +-- user_agent.py                  # Simulated user personas
|   +-- README.md
|
+-- user_profiles/
|   +-- generate_profiles.py           # Script to generate profiles.json
|   +-- profiles.json                  # 5 users x 50 scenarios = 250 scenarios
|
+-- history/                           # [Generated] Conversation logs
|   +-- user_N/
|       +-- session_001.json           # Full turn-by-turn conversation
|       +-- ... (50 sessions per user)
|
+-- analyzer/                          # Phase 2: Pattern extraction + swarm gen
|   +-- analyze_history.py             # Main entry point
|   +-- pattern_extractor.py           # LLM-based pattern clustering
|   +-- swarm_generator.py             # Generates mini-agent .py files + embeddings
|   +-- trigger_schema.py              # Feature schema, extraction prompts, binary questionnaires, matching logic
|   +-- trigger_matcher.py             # Shared trigger matching pipeline (used by validation + runtime)
|   +-- llm_util.py                    # Shared LLM utilities
|   +-- README.md
|
+-- swarms/                            # [Generated] Mini-agent swarms per user
|   +-- user_N/
|       +-- manifest.json              # Index of all agents + metadata + critic results
|       +-- triggers.json              # Trigger definitions + scope embeddings (768-dim)
|       +-- user_style.json            # Behavioral pattern profile
|       +-- agents/
|           +-- python_advanced_debugging.py
|           +-- ... (quality-based count, typically 5-10 per user)
|
+-- augmented_assistant_agent/         # Phase 3: Swarm-augmented agent
|   +-- __init__.py
|   +-- agent.py                       # ADK Agent with check_and_invoke_swarm + baseline_assistant (AgentTool)
|   +-- .env
|   +-- requirements.txt
|   +-- tools/
|       +-- active_mem.py              # Trigger matching + mini-agent invocation + hallucination detection
|       +-- swarm_loader.py            # Dynamic module loading + caching
|       +-- search_agent.py            # [UNUSED] Web search sub-agent (kept for future re-enablement)
|
+-- eval/                              # Eval pool generation + sampling + shared harness
|   +-- generate_eval_pool.py          # Synthesize test cases from history (LLM)
|   +-- sample_eval_scenarios.py       # Sample balanced eval sets (embedding + keyword + LLM review)
|   +-- harness.py                     # Shared eval functions (run_eval_user_turn, judge_conversation, etc.)
|
+-- eval_pool/                         # [Generated] Synthetic test case pools
|   +-- user_N/
|       +-- pool.json                  # N synthetic cases per session, grouped by intent
|
+-- test_augmented_agent.py            # Phase 4: Comparative evaluation
+-- evaluation_rubric.md               # Baseline rubric (8 dimensions)
+-- evaluation_rubric_augmented.md     # Augmented rubric (10 dimensions)
+-- evaluation_scenarios_user_[1-5].json # Held-out eval scenarios (18 per user)
+-- evaluation_output/                 # [Generated] JSON evaluation reports
|
+-- run_pipeline.sh                    # Full pipeline: analyze -> evaluate (with cleanup)
+-- test_deployed_agent.py             # Baseline agent tests (standalone)
+-- pyproject.toml                     # Root dependencies (uv project)
+-- uv.lock                            # Pinned dependency lockfile
+-- .gitignore
+-- llms.txt                           # ADK documentation reference
```

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (Python package & environment manager)
- Google Cloud SDK (`gcloud`) authenticated
- Access to Google Cloud with Gemini models enabled

### Install

```bash
# Clone and enter the project
cd ADK_agents

# Create the virtual environment and install all dependencies
# (uv reads pyproject.toml and pins versions in uv.lock)
uv sync

# Authenticate with Google Cloud
gcloud auth application-default login
```

> **Running commands:** all `python` / `adk` commands below assume the
> uv-managed environment. Either prefix each command with `uv run`
> (e.g. `uv run python harvest/orchestrator.py`, `uv run adk web`), or
> activate the environment once with `source .venv/bin/activate` and run
> the commands as written.

### Configuration

Each agent directory has a `.env` file:

```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

---

## Running the Pipeline

### Phase 1: Harvest Conversational History

```bash
# Test run: 3 scenarios for one user
python harvest/orchestrator.py --user user_1 --limit 3 --verbose

# Full run: all 50 scenarios for one user
python harvest/orchestrator.py --user user_1 --verbose

# Resume (skip existing sessions)
python harvest/orchestrator.py --user user_1 --resume

# All users (250 sessions total)
python harvest/orchestrator.py
```

**Output:** `history/{user_id}/session_{NNN}.json`

### Phase 2: Analyze & Generate Swarms

```bash
# Preview extracted patterns (no file generation)
python analyzer/analyze_history.py --user user_1 --dry-run --verbose

# Generate swarms (with critic pass)
python analyzer/analyze_history.py --user user_1 --verbose

# Skip critic pass (faster, lower quality)
python analyzer/analyze_history.py --user user_1 --verbose --skip-critic

# All users
python analyzer/analyze_history.py --verbose
```

**Output:** `swarms/{user_id}/manifest.json`, `triggers.json`, `user_style.json`, `agents/*.py`

### Phase 3: Test the Augmented Agent Interactively

```bash
# Run via ADK web UI
adk web
# Select "augmented_assistant" from the agent dropdown
```

> **Gotcha — swarms never fire in the Dev UI (`user_id` mismatch):** The ADK
> Dev UI hardcodes `user_id="user"` for every session, but swarms are stored
> per user as `swarms/user_1/`, `swarms/user_2/`, etc. `load_swarm("user")`
> finds no `swarms/user/` directory, returns empty triggers, and
> `check_and_invoke_swarm` short-circuits to `{"action": "none"}` — so the
> agent silently answers as the plain baseline and no swarm ever fires. To
> test a specific user's swarm through the UI, point `swarms/user` at that
> user's directory (`swarms/` is gitignored, so this is dev-only):
>
> ```bash
> ln -sfn user_1 swarms/user   # now the Dev UI's "user" resolves to user_1's swarm
> ```
>
> The swarm loader **caches per `user_id`**, so restart `adk web` after
> creating or re-pointing the symlink. Then ask a question that matches an
> agent's *scope* — e.g. for `user_1`'s `gcp_k8s_network_troubleshooting`
> agent: *"My GKE pods are getting intermittent connection resets through the
> internal load balancer and sporadic 502s — how do I debug this?"* (a
> troubleshooting question; "help me build a cluster" is a create task and
> won't match). For proper per-user testing, use `test_augmented_agent.py`,
> which passes the real `user_id` directly.
>
> **Gotcha — blocked default port:** `adk web` listens on port `8000` by
> default. If your environment disallows it, pass an allowed port (and, when
> reaching the UI through a proxy origin, an allowed-origins pattern so
> state-changing POSTs aren't rejected with `403 Forbidden`):
>
> ```bash
> adk web --port 8080 --host 0.0.0.0 --allow_origins "regex:.*"
> ```

### Phase 3.5: Generate Eval Pool & Sample Scenarios

After harvest (Phase 1) and swarm generation (Phase 2), generate a pool of synthetic test cases and sample balanced evaluation scenarios.

```bash
# Generate eval pool from conversation history (run once after harvest)
python eval/generate_eval_pool.py --user user_4              # single user
python eval/generate_eval_pool.py                            # all users
python eval/generate_eval_pool.py --user user_4 -n 3         # 3 cases per session (default: 2)
python eval/generate_eval_pool.py --user user_4 --dry-run    # preview without LLM calls

# Sample balanced eval scenarios from pool (run after swarm generation)
python eval/sample_eval_scenarios.py --user user_4 --seed 42      # 20 scenarios (default)
python eval/sample_eval_scenarios.py --user user_4 --total 10     # custom count
python eval/sample_eval_scenarios.py                              # all users
```

The **pool generator** reads historic sessions, groups by intent, and uses Gemini 3.1 Pro (with fallback to 3 Pro / 2.5 Pro) to synthesize N new test cases per session — same intent, different scenario. The pool is independent of the swarm and can be generated once after harvest.

The **sampler** uses a three-layer matching system to classify pool entries as "relevant" (should trigger an agent) or "not relevant" (should not):

1. **Embedding similarity** (primary) — embeds a representative opening message per intent via `text-embedding-005` and compares against all agents' scope embeddings (threshold 0.35). Handles paraphrasing and domain overlap naturally.
2. **Substring keyword matching** (fallback) — matches intent words against agent names, descriptions, and keywords using substring matching (`"troubleshoot" in "troubleshooting"`) instead of exact word equality. Catches stemming variants when embeddings are unavailable.
3. **LLM review** (confirmation) — Gemini 2.5 Pro reviews all candidates and independently judges whether each message would trigger an agent. The review prompt does not reveal the expected category to avoid anchoring bias.

Default: 20 scenarios per user (10 similar + 10 different). Output is `evaluation_scenarios_{user_id}.json` — compatible with the test harness.

### Phase 4: Run Comparative Evaluation

Scenarios can come from auto-generated pools (recommended) or hand-crafted JSON files.

```bash
# Using dedicated held-out evaluation scenarios (recommended)
python test_augmented_agent.py --eval-file evaluation_scenarios_user1.json --verbose          # user_1
python test_augmented_agent.py --eval-file evaluation_scenarios_user2.json --verbose          # user_2
python test_augmented_agent.py --eval-file evaluation_scenarios_user3.json --verbose          # user_3
python test_augmented_agent.py --eval-file evaluation_scenarios_user4.json --verbose          # user_4
python test_augmented_agent.py --eval-file evaluation_scenarios_user5.json --verbose          # user_5

# With LLM-as-judge quality scoring
python test_augmented_agent.py --eval-file evaluation_scenarios_user1.json --judge --verbose

# Calibrate embedding similarity thresholds for a specific user
python test_augmented_agent.py --calibrate-embeddings --user user_1

# Sampling from profiles.json (legacy mode)
python test_augmented_agent.py -n 5 --seed 42 --verbose --judge

# Run only augmented agent (skip baseline)
python test_augmented_agent.py --eval-file evaluation_scenarios_user1.json --augmented-only --verbose
```

**CLI flags:**

| Flag | Description |
|------|-------------|
| `--eval-file FILE` | Use dedicated held-out evaluation scenarios (default 20 per user: 10 similar + 10 different) |
| `-n N` | Number of scenarios per user when sampling from profiles.json (default: 2) |
| `--user USER_ID` | Run for a specific user only |
| `--seed N` | Random seed for reproducible scenario sampling (default: 42) |
| `--judge` / `-j` | Enable LLM-as-judge scoring (Gemini 3.1 Pro, fallback to 2.5 Pro) |
| `--verbose` / `-v` | Show full conversation turns |
| `--baseline-only` | Skip augmented agent |
| `--augmented-only` | Skip baseline agent |
| `--calibrate-embeddings` | Print embedding similarity distributions for threshold tuning (requires `--user`) |

**Output:** `evaluation_output/{timestamp}_final_eval.json` (eval-file mode) or `evaluation_output/{timestamp}_comparison.json` (sampling mode)

### Full Pipeline (Analyze + Evaluate)

```bash
# Run full pipeline for default users (1,2,3,4,5)
./run_pipeline.sh

# Specific users only
./run_pipeline.sh user_1 user_3

# Skip critic pass (faster)
./run_pipeline.sh --skip-critic
```

The pipeline script cleans stale swarm agents before regenerating (prevents old agents from interfering via glob-based loading), then samples eval scenarios from the pool (if available, with LLM review), and runs evaluation sequentially for each user.

---

## Evaluation Methodology

### User-Agent-Driven Approach

Unlike traditional evaluation where test cases have hardcoded expected turn counts, this evaluation uses a **simulated user agent** that autonomously drives conversations. The user agent:

1. Receives the same persona and intent used during harvest (from `profiles.json`)
2. Sends the same opening message to both agents
3. After each assistant response, decides whether the goal is fully achieved
4. If achieved, signals `[GOAL_REACHED]` — otherwise generates a contextual follow-up
5. A max-turn cap (default: 6) prevents runaway conversations

This ensures the evaluation is **fair** — both agents receive identical input and the user agent applies the same satisfaction criteria to both. Turn reduction is measured by how quickly each agent satisfies the user agent's goal, not by artificially hardcoded turn counts.

### Scenario Sampling

Scenarios are sampled from `profiles.json` using round-robin per-intent selection to maximize diversity. For example, with `-n 3` and a user who has 10 intents, the sampler picks one scenario from 3 different intents rather than 3 from the same intent.

### Rubric: 10 Dimensions

The evaluation rubric scores responses on a 1-4 scale across 10 dimensions:

**Baseline Dimensions (1-8):**

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| Accuracy | Critical | Factual correctness (fabrication = overall score capped at 1) |
| Helpfulness | High | Does the response solve the user's problem? |
| Source Usage | High | Appropriate citation of web search results |
| Clarity | Medium | Well-structured, easy to follow |
| Conciseness | Medium | Thorough but not verbose |
| Tone | Medium | Appropriate for the user and context |
| Multi-Part Handling | Medium | Addresses all parts of multi-part questions |
| Multilingual | Medium | Responds in the user's language |

**Swarm-Specific Dimensions (9-10):**

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| Personalization | High | Combines proactive intelligence and preference alignment: did the agent anticipate needs and match known format/tone/detail? |
| Turn Efficiency | Medium | Did the user get what they needed in fewer back-and-forths? |

### LLM-as-Judge (Head-to-Head)

Evaluation uses Gemini 3.1 Pro as an automated judge (with automatic fallback to 2.5 Pro on quota errors) conducting a **head-to-head comparison**. The judge runs at temperature 1.0. For each test scenario, the judge receives:
- **Both** the baseline agent's full conversation log and the augmented agent's conversation log
- Whether each agent's user reached `[GOAL_REACHED]` vs hit max turns
- The user's persona and intent
- The full 10-dimension scoring rubric

The judge scores **both** agents on every applicable dimension, then declares a **winner** with a written justification. A key consideration for the judge is whether the augmented agent reached the goal in fewer turns while maintaining or improving quality.

Output per test case:
```json
{
  "baseline": {"scores": {...}, "overall_score": 3.0},
  "augmented": {"scores": {...}, "overall_score": 3.5},
  "comparison": {
    "winner": "augmented",
    "quality_delta": 0.5,
    "summary": "The augmented agent provided a comprehensive..."
  }
}
```

### Split Reporting

Results are reported in two groups:
- **Similar scenarios** — tests where the user's intent matches a generated agent (should trigger — the real test of the system)
- **Different scenarios** — tests where no swarm should fire (false positive test)

This split makes it clear how much value the swarms add vs the baseline agent's inherent multi-turn exploration.

---

## Evaluation Results

### Pipeline Status (Latest Run: 2026-04-29)

All 5 users have been fully processed through the latest pipeline version (V8: two-stage matching with binary questionnaires, parallel generation with best-pick, post-generation fact-check, fabrication hard-ceiling in critic, mini-eval harness for validation gate, grounding instructions in agent generation).

| User | Persona | Sessions | Task Agents | Eval Scenarios |
|------|---------|----------|-------------|----------------|
| `user_1` | Software engineer (Python, Google Cloud) | 50 | 1 | 18 |
| `user_2` | Marketing manager | 50 | 6 | 18 |
| `user_3` | ML graduate student | 50 | 6 | 18 |
| `user_4` | Small business owner (cafe) | 50 | 5 | 18 |
| `user_5` | Travel enthusiast + home cook | 50 | 5 | 18 |

**Total:** 250 sessions harvested, 23 task agents (quality-based count per user, 1-6), 90 evaluation scenarios (18 per user: 10 similar + 8 different).

### Generated Swarms Overview

**user_1** (1 task agent + `user_style.json`): `advanced_docker_configuration`

**user_2** (6 task agents + `user_style.json`): `ab_testing_strategy`, `analyze_marketing_metrics`, `comprehensive_marketing_strategy`, `email_copywriting_and_campaigns`, `executive_presentation_outlining`, `social_media_content_creation`

**user_3** (6 task agents + `user_style.json`): `compare_ml_architectures`, `dataset_discovery`, `debug_model_training`, `ml_technical_and_math_deep_dive`, `nlp_experiment_design`, `nlp_statistical_evaluation`

**user_4** (5 task agents + `user_style.json`): `business_insurance_inquiries`, `cafe_management_operations`, `cafe_menu_pricing`, `small_business_tax_prep`, `supplier_management`

**user_5** (5 task agents + `user_style.json`): `beverage_pairing_advice`, `budget_travel_planning`, `cultural_etiquette_guidance`, `recipe_and_meal_planning`, `travel_dining_recommendations`

### Trigger Accuracy

Each user was evaluated with held-out scenarios: **similar** (should trigger the correct swarm agent) and **different** (should NOT trigger any swarm — false positive test). Default is 18 scenarios per user (10 similar + 8 different).

> All results below are from the V8 pipeline run (2026-04-29): two-stage matching, fabrication hard-ceiling, parallel generation, mini-eval validation gate.

| User | Similar Fire Rate | Different FP Rate | Notes |
|------|-------------------|-------------------|-------|
| `user_1` | 5/10 (50%) | 1/8 | Only 1 agent survived validation; fires broadly on Docker-adjacent intents |
| `user_2` | **10/10 (100%)** | **0/8** | Perfect — every similar scenario fires an agent, zero false positives |
| `user_3` | 9/10 (90%) | 3/8 | High fire rate; 3 FP on out-of-domain (astronomy, pet_care, parenting) |
| `user_4` | 6/10 (60%) | 2/8 | Improved from V7's 3 wrong-agent misroutes; 2 FP (parenting, car_repair) |
| `user_5` | 6/10 (60%) | 2/8 | `budget_travel_planning` over-triggers on unrelated different scenarios |
| **Total** | **36/50 (72%)** | **8/40 (20%)** | |

### Quality: Head-to-Head (V8 — All Users)

All results on a 1-4 judge scale across three dimensions: **accuracy**, **helpfulness**, and **personalization**. Results focus on similar scenarios where a mini-agent fired, since when no mini-agent fires, both agents behave equivalently (augmented delegates to the baseline sub-agent).

#### Why Mini-Agent Triggering Matters

When no mini-agent fires, the augmented agent delegates to its `baseline_assistant` (AgentTool) — producing functionally identical output. Any win/loss differences in the "not fired" group are noise from LLM non-determinism. The real test of the system is **similar scenarios where a mini-agent fires**: this is where personalization, domain expertise, and swarm quality make a measurable difference.

---

**user_1** (software engineer, 1 agent: `advanced_docker_configuration`):

*Similar — Mini-Agent Fired (5/10):*

| Scenario | Intent | Agent | B (acc/help/pers) | A (acc/help/pers) | Winner |
|----------|--------|-------|-------------------|-------------------|--------|
| sim_001 | write_dockerfile | advanced_docker_configuration | 4/4/3 | 1/1/2 | Baseline |
| sim_002 | refactor_legacy_code | advanced_docker_configuration | 4/4/2 | 4/4/4 | **Augmented** |
| sim_005 | refactor_legacy_code | advanced_docker_configuration | 4/4/2 | 4/4/4 | **Augmented** |
| sim_009 | deploy_gcp_service | advanced_docker_configuration | 4/4/2 | 4/4/4 | **Augmented** |
| sim_010 | configure_ci_cd | advanced_docker_configuration | 4/4/2 | 2/2/3 | Baseline |
| | | **Avg** | **4.00/4.00/2.20** | **3.00/3.00/3.40** | **3W-2L** |

With only 1 surviving agent, `advanced_docker_configuration` fires for all matched scenarios — even non-Docker intents like `refactor_legacy_code`. When the intent aligns (refactor, deploy), the personalization boost (+1.20) drives wins. When it doesn't (write_dockerfile, configure_ci_cd), accuracy drops significantly (acc=1, acc=2).

*Similar — Not Fired (5/10):* 3W-2L (noise — both agents behave as baseline)
*Different (8 scenarios):* 5W-1L-2T
*Overall:* **11W-5L-2T**

---

**user_2** (marketing manager, 6 agents):

*Similar — Mini-Agent Fired (10/10 — perfect fire rate):*

| Scenario | Intent | Agent | B (acc/help/pers) | A (acc/help/pers) | Winner |
|----------|--------|-------|-------------------|-------------------|--------|
| sim_001 | write_campaign_copy | email_copywriting_and_campaigns | 4/4/1 | 4/4/4 | **Augmented** |
| sim_002 | draft_email_newsletter | email_copywriting_and_campaigns | 4/4/1 | 4/3/4 | **Augmented** |
| sim_003 | create_brand_guidelines | social_media_content_creation | 4/4/1 | 4/4/4 | **Augmented** |
| sim_004 | plan_event | comprehensive_marketing_strategy | 4/4/2 | 4/4/4 | **Augmented** |
| sim_005 | draft_email_newsletter | email_copywriting_and_campaigns | 4/4/2 | 4/4/4 | **Augmented** |
| sim_006 | plan_campaign_strategy | comprehensive_marketing_strategy | 4/4/1 | 4/4/4 | **Augmented** |
| sim_007 | analyze_marketing_metrics | comprehensive_marketing_strategy | 4/4/2 | 4/4/3 | **Augmented** |
| sim_008 | create_brand_guidelines | executive_presentation_outlining | 4/4/2 | 4/4/4 | **Augmented** |
| sim_009 | conduct_ab_test | executive_presentation_outlining | 4/4/1 | 4/4/4 | **Augmented** |
| sim_010 | analyze_competitor | comprehensive_marketing_strategy | 4/4/1 | 4/4/4 | **Augmented** |
| | | **Avg** | **4.00/4.00/1.40** | **4.00/3.90/3.90** | **10W-0L** |

**Gold standard.** 100% fire rate, 100% win rate, zero accuracy loss (4.00 → 4.00), zero false positives. Personalization jumps from 1.40 to 3.90 (+2.50). The marketing domain produces well-separated, high-quality agents that consistently deliver preference-aligned output.

*Different (8 scenarios):* 6W-1L-1T
*Overall:* **16W-1L-1T**

---

**user_3** (ML grad student, 6 agents):

*Similar — Mini-Agent Fired (9/10):*

| Scenario | Intent | Agent | B (acc/help/pers) | A (acc/help/pers) | Winner |
|----------|--------|-------|-------------------|-------------------|--------|
| sim_001 | summarize_ml_concept | nlp_statistical_evaluation | 4/4/1 | 4/4/3 | **Augmented** |
| sim_002 | explain_statistical_test | nlp_statistical_evaluation | 4/4/2 | 1/4/4 | Baseline |
| sim_003 | design_experiment | nlp_experiment_design | 4/4/2 | 4/4/3 | **Augmented** |
| sim_005 | explain_statistical_test | nlp_statistical_evaluation | 4/4/2 | 3/4/4 | **Augmented** |
| sim_006 | find_datasets | compare_ml_architectures | 1/3/1 | 1/3/4 | **Augmented** |
| sim_007 | debug_training_loop | debug_model_training | 4/4/2 | 4/4/4 | **Augmented** |
| sim_008 | design_experiment | nlp_experiment_design | 4/4/1 | 4/4/4 | **Augmented** |
| sim_009 | derive_math_proof | ml_technical_and_math_deep_dive | 4/4/1 | 3/4/3 | **Augmented** |
| sim_010 | compare_model_architectures | ml_technical_and_math_deep_dive | 4/4/1 | 4/4/4 | **Augmented** |
| | | **Avg** | **3.67/3.89/1.44** | **3.11/3.89/3.67** | **8W-1L** |

Strong personalization gain (+2.23) with a moderate accuracy trade-off (3.67 → 3.11). The one loss (sim_002, acc=1) was a hallucination by the augmented agent on a statistical test explanation. Despite this, 8/9 scenarios won.

*Similar — Not Fired (1/10):* 1W-0L
*Different (8 scenarios):* 5W-1L-1T (1 unjudged)
*Overall:* **14W-2L-1T**

---

**user_4** (small business/cafe owner, 5 agents):

*Similar — Mini-Agent Fired (6/10):*

| Scenario | Intent | Agent | B (acc/help/pers) | A (acc/help/pers) | Winner |
|----------|--------|-------|-------------------|-------------------|--------|
| sim_002 | legal_questions | business_insurance_inquiries | 4/4/2 | 4/4/4 | **Augmented** |
| sim_006 | menu_pricing | cafe_menu_pricing | 4/4/2 | 4/4/4 | **Augmented** |
| sim_007 | customer_feedback | cafe_management_operations | 4/4/1 | 4/4/3 | **Augmented** |
| sim_008 | hiring_process | cafe_management_operations | 4/4/1 | 4/4/4 | **Augmented** |
| sim_009 | financial_planning | small_business_tax_prep | 4/4/2 | 4/4/4 | **Augmented** |
| sim_010 | business_insurance | business_insurance_inquiries | 4/4/2 | 4/4/4 | **Augmented** |
| | | **Avg** | **4.00/4.00/1.67** | **4.00/4.00/3.83** | **6W-0L** |

**Dramatic turnaround from V7.** Previously user_4 was the weakest (1W-5L with -1.50 delta and 3 wrong-agent misroutes). V8's tighter validation, better agent boundaries, and questionnaire-based disambiguation produced **6W-0L with zero accuracy loss** (4.00 → 4.00) and +2.17 personalization gain. Zero wrong-agent misroutes.

*Similar — Not Fired (4/10):* 4W-0L
*Different (8 scenarios):* 7W-0L-1T
*Overall:* **17W-0L-1T**

---

**user_5** (travel + cooking, 5 agents):

*Similar — Mini-Agent Fired (6/10):*

| Scenario | Intent | Agent | B (acc/help/pers) | A (acc/help/pers) | Winner |
|----------|--------|-------|-------------------|-------------------|--------|
| sim_001 | travel_packing | cultural_etiquette_guidance | 4/4/2 | 4/4/4 | **Augmented** |
| sim_003 | find_recipe | recipe_and_meal_planning | 4/4/2 | 4/4/4 | **Augmented** |
| sim_005 | meal_prep | recipe_and_meal_planning | 4/4/2 | 4/4/4 | **Augmented** |
| sim_008 | find_recipe | recipe_and_meal_planning | 4/3/1 | 4/3/4 | **Augmented** |
| sim_009 | cultural_etiquette | cultural_etiquette_guidance | 4/4/2 | 4/4/4 | **Augmented** |
| sim_010 | budget_travel | budget_travel_planning | 4/4/3 | 4/4/2 | Baseline |
| | | **Avg** | **4.00/3.83/2.00** | **4.00/3.83/3.67** | **5W-1L** |

Accuracy held perfectly (4.00 → 4.00), personalization up +1.67. The one loss (sim_010, budget_travel) was a minor personalization regression (3→2) — likely noise since accuracy and helpfulness were identical.

*Similar — Not Fired (4/10):* 1W-3L (noise — baseline-equivalent behavior)
*Different (8 scenarios):* 6W-2L
*Overall:* **12W-6L**

---

### Aggregate Results (V8 — All Users)

#### Mini-Agent Fired: The Core Metric

When a mini-agent fires, the augmented agent delivers a personalized, domain-expert response. This is the scenario that tests whether the swarm adds value. **When no mini-agent fires, both agents produce essentially the same output** (augmented delegates to baseline), so wins/losses in that group are noise.

**Similar scenarios where swarm fired (36 scenarios):**

| User | Fired | W-L-T | Accuracy (B→A) | Personalization (B→A) | Notes |
|------|-------|-------|-----------------|----------------------|-------|
| `user_1` | 5 | 3-2-0 | 4.00→3.00 (-1.00) | 2.20→3.40 (+1.20) | Single agent over-triggers; accuracy drops on misaligned intents |
| `user_2` | 10 | **10-0-0** | 4.00→4.00 (0.00) | 1.40→3.90 (+2.50) | Perfect — zero accuracy loss, massive personalization |
| `user_3` | 9 | **8-1-0** | 3.67→3.11 (-0.56) | 1.44→3.67 (+2.23) | One hallucination (acc=1); 8/9 won |
| `user_4` | 6 | **6-0-0** | 4.00→4.00 (0.00) | 1.67→3.83 (+2.17) | Dramatic V7→V8 turnaround (was 1-5) |
| `user_5` | 6 | **5-1-0** | 4.00→4.00 (0.00) | 2.00→3.67 (+1.67) | One minor personalization dip |
| **Total** | **36** | **32-4-0 (88.9%)** | **3.92→3.64 (-0.28)** | **1.67→3.72 (+2.05)** | |

**Win rate when mini-agent fires: 88.9%** (32W-4L). Personalization improves by +2.05 on average (1.67 → 3.72). Accuracy cost is -0.28 overall, concentrated in user_1 (single over-broad agent) and user_3 (one hallucination).

#### Scores Breakdown by Trigger Status

| Scope | Pipeline | Accuracy | Helpfulness | Personalization |
|-------|----------|----------|-------------|-----------------|
| Similar + FIRED (36) | Baseline | 3.92 | 3.94 | 1.67 |
| Similar + FIRED (36) | Augmented | 3.64 | 3.78 | **3.72** |
| Similar + NOT FIRED (14) | Baseline | 3.71 | 3.71 | 1.64 |
| Similar + NOT FIRED (14) | Augmented | 3.57 | 3.79 | 2.57 |
| Different (39 scored) | Baseline | 3.92 | 3.85 | 1.72 |
| Different (39 scored) | Augmented | 3.90 | 3.90 | 2.95 |
| **All (89 scored)** | **Baseline** | **3.89** | **3.87** | **1.69** |
| **All (89 scored)** | **Augmented** | **3.74** | **3.83** | **3.20** |

#### Overall Win/Loss/Tie

| Scope | W | L | T | Win Rate |
|-------|---|---|---|----------|
| Similar + swarm FIRED | **32** | 4 | 0 | **88.9%** |
| Similar + swarm NOT FIRED | 9 | 5 | 0 | 64.3% |
| Different | 29 | 5 | 5 | 74.4% |
| **Overall (89 scored)** | **70** | **14** | **5** | **78.7%** |

#### Trigger Accuracy Summary

| User | Similar Fire Rate | Different FP | Overall Trigger Accuracy |
|------|-------------------|--------------|--------------------------|
| `user_1` | 5/10 | 1/8 | 12/18 (67%) |
| `user_2` | **10/10** | **0/8** | **18/18 (100%)** |
| `user_3` | 9/10 | 3/8 | 12/18 (67%) |
| `user_4` | 6/10 | 2/8 | 11/18 (61%) |
| `user_5` | 6/10 | 2/8 | 12/18 (67%) |
| **Total** | **36/50 (72%)** | **8/40 (20%)** | **65/90 (72%)** |

### Pipeline Iteration History

| Version | Key Changes | Similar Fired W-L-T | Notes |
|---------|-------------|---------------------|-------|
| **V1** (keyword) | keyword_and_context triggers, no behavioral separation | 8W-14L | |
| **V2** (LLM-match) | Two-stage LLM triggers, behavioral separation | 13W-12L | |
| **V3** (attribute_match) | Attribute-based feature extraction + programmatic rules | 14W-10L | |
| **V4** (embeddings) | Scope embeddings + task-adaptive style dampening | 16W-8L-1T | |
| **V4.1** (review fixes) | Two-tier agent selection, critic split, prompt caps | 8W-0L-1T | |
| **V5** (semantic-only) | Soft penalty filters, pure embedding matching, coverage validation | 8W-0L-1T | |
| **V6** (non-parametric) | Non-parametric agent selection, google_search sub-agent | 23W-11L-3T | |
| **V7** (hallucination guard) | First-message hallucination guard, fair eval (no web search/memory) | 29W-8L-3T | 82% excl. user_4 |
| **V8** (questionnaire + grounding) | Two-stage matching (binary questionnaires), parallel generation with best-pick, post-gen fact-check, fabrication hard-ceiling in critic, mini-eval validation gate | **32W-4L (88.9%)** | user_4: 1W-5L → **6W-0L** |

### Key Observations

1. **Mini-agent fired win rate: 88.9% (32W-4L)** — up from 73% in V7 (29W-8L-3T). The primary improvement comes from user_4 flipping from 1W-5L to 6W-0L, and user_2 achieving a perfect 10W-0L.

2. **Personalization is the primary driver (+2.05 when fired).** Accuracy and helpfulness remain close to baseline; personalization jumps from 1.67 to 3.72 on average. This confirms the core thesis: mini-agents deliver preference-aligned responses that generic assistants cannot.

3. **user_4 dramatic turnaround.** V7's worst performer (1W-5L, -1.50 delta, 3 wrong-agent misroutes, 3 catastrophic failures) became V8's strongest improvement: **6W-0L, zero accuracy loss, +2.17 personalization, zero wrong-agent misroutes**. The combination of tighter validation (mini-eval harness), better agent boundaries (5 more-distinct agents vs 4 overlapping ones), and questionnaire-based disambiguation eliminated the cafe-domain confusion.

4. **user_2 is the gold standard** — 100% fire rate, 100% win rate, zero false positives, zero accuracy loss, +2.50 personalization. The marketing domain produces well-separated agents with clear boundaries.

5. **Accuracy trade-off is small and concentrated.** Overall accuracy delta is -0.28 (3.92→3.64). The 4 losses across all users are: user_1 sim_001 (acc=1, Docker agent on Dockerfile intent — wrong approach), user_1 sim_010 (acc=2, Docker agent on CI/CD intent), user_3 sim_002 (acc=1, hallucinated statistical content), and user_5 sim_010 (minor personalization dip). Three of four are user_1's single over-broad agent.

6. **False positive rate (20%) is non-damaging.** 8/40 different scenarios triggered a mini-agent when they shouldn't have. However, in most cases (5/8), the augmented agent still won or tied despite the false positive — the user preferences embedded in the agent's prompt compensate even when the wrong agent fires.

7. **When no mini-agent fires, results are noise.** The "not fired" similar group shows 9W-5L (64.3%), but since both agents produce baseline-equivalent output in this case, these differences come from LLM non-determinism, not system design. The meaningful comparison is exclusively in the "fired" group.

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Local-first execution** | Orchestrator and analyzer run locally via ADK's `InMemoryRunner` — no deployment needed for development |
| **LLM-generated swarms** | Pattern extraction and swarm generation use Gemini 3.1 Pro (stronger reasoning, requires `location="global"`). Runtime uses Gemini 3 Flash Preview (faster, cheaper) |
| **Two-stage matching (V8)** | Stage 1: soft penalty embedding matching (domain/task_type mismatches apply 0.15/0.10 penalties). Stage 2: binary questionnaire disambiguation — 3-5 contrastive yes/no questions per agent evaluated in parallel, combined score (40% embedding + 60% questionnaire). This replaces the simple embedding-gap tiebreaker with a more precise disambiguation mechanism |
| **No keyword matching** | Keyword-based matching (`require_any_keyword`, `exclude_keywords`) removed entirely from generation and runtime. Substring matching caused false positives ("pr" matching "process") and orphaned exclusions blocking valid routes after ranking. Pure embedding + questionnaire matching is more robust |
| **Pre-computed scope embeddings** | Each agent's scope (description + trigger signals + typical flow) is embedded at generation time and stored in `triggers.json`. Runtime only needs to embed the user message (1 API call) |
| **Coverage validation after ranking** | When ranking drops agents below the quality threshold, dropped agents' patterns are checked for coverage gaps. Orphaned patterns are absorbed by the closest surviving agent (by embedding similarity), with domain expansion and exclusion removal. Prevents user needs from falling through the cracks |
| **Response post-processing** | Conversational tails ("Is there anything else?") are stripped and unfenced code blocks are auto-wrapped in markdown fences. Applied at runtime in `active_mem.py` before returning the response |
| **Task-adaptive style dampening** | Detects complex tasks (financial plans, pricing strategies) and overrides conflicting style constraints ("bite-sized", "one concept at a time") that would force fragmentation into multiple turns |
| **Agent prompt priority** | Agent-specific instructions (ENRICHED_PROMPT) take precedence over runtime STYLE INSTRUCTIONS when they conflict, preventing style from overriding domain expertise |
| **Behavioral/task pattern separation** | Behavioral patterns (how user communicates) become a shared `user_style.json` instead of standalone agents. Prevents false positives from communication-style triggers firing on unrelated topics |
| **User style sanitization** | Harmful phrases in user_style.json ("incomplete thought", "gentle nudge", "accidental send") are detected and replaced at generation time to prevent agents from treating normal messages as unfinished |
| **Critic pass against gold references** | Validates agent output by running `execute()` against real history and comparing to the actual assistant response that worked. Grounds quality checks in what the user actually wanted, not abstract criteria. V8 added a fabrication hard-ceiling: >= 2 factual contradictions caps score at 4/10 |
| **Parallel generation with best-pick (V8)** | Each agent is generated twice at temperatures 0.2 and 0.35. A Flash LLM selects the more grounded candidate. Reduces fabrication by providing diversity and selecting the safer option |
| **Post-generation fact-check (V8)** | Flash LLM scans each agent's ENRICHED_PROMPT for fabricated claims (API names, CLI flags, URLs). LOW-confidence claims are revised to include uncertainty caveats rather than stated as fact |
| **Mini-eval validation gate (V8)** | Validation uses the same multi-turn eval harness as Phase 4, with scenarios seeded from 50 historic conversations. Ensures validation quality is representative of actual final evaluation (replaces the simpler single-turn `_quick_judge`) |
| **Semantic trigger evaluation** | Evaluation uses LLM-based semantic matching (with agent name normalization for suffix variations) instead of exact agent name comparison, making results robust to swarm regeneration |
| **Two invocation modes** | Auto (silent, for high-confidence matches) and Suggest (human-in-the-loop, for lower confidence) |
| **Swarms as plain Python files** | Mini-agents are `.py` files on disk — easy to inspect, edit, and version control. No database required |
| **Non-parametric agent selection** | No fixed target count — every agent scoring >= 25/50 on the 5-dimension rubric (VALUE×3, DISTINCTIVENESS×2, TRIGGER_CLARITY×2, QUALITY×2, FREQUENCY×1) is kept. LLM-based ranking (Gemini 3.1 Pro with fallback) evaluates all candidates and can veto redundant/weak agents. Hard safety cap at 30 (cost guardrail only). Falls back to frequency-based filtering (>= 4 sessions, min 3) on LLM failure. Constants: `HARD_CAP_AGENTS=30`, `MIN_QUALITY_SCORE=25` in `swarm_generator.py` |
| **Fair evaluation parity** | Both agents run without web search or memory tools. The baseline `user_assistant_agent/` uses `tools=[]` and the augmented agent uses `tools=[check_and_invoke_swarm]`. This isolates the swarm's contribution from infrastructure differences |
| **First-message hallucination guard** | Three-layer defense: (1) empty history injects explicit "This is the FIRST message" note, (2) runtime regex detects fabricated context ("as we discussed", "your message was cut off"), (3) critic pass includes a HALLUCINATION criterion that scores fabricated context as 0 |

---

## Limitations & Future Work

### Current Limitations

- **user_1 agent survival** — Only 1 of the original agents survived V8's tighter validation gate, leaving a single `advanced_docker_configuration` agent that over-triggers on non-Docker intents. The 50% fire rate and accuracy drops (acc=1 on Dockerfile, acc=2 on CI/CD) indicate the agent needs better scope boundaries or the validation threshold needs tuning to let more agents survive.
- **False positive rate (20%)** — 8/40 different scenarios triggered agents when they shouldn't have. While rarely damaging (augmented still wins 5/8), this adds unnecessary latency and could confuse users in production. user_3 has the highest FP rate (3/8).
- **Accuracy vs personalization trade-off** — Overall accuracy drops -0.28 when mini-agents fire (3.92 → 3.64). The worst cases are concentrated fabrications (user_1 sim_001 acc=1, user_3 sim_002 acc=1). The fact-check and fabrication hard-ceiling mitigate but don't eliminate this.
- **No web search capability** — Web search was removed from both agents for fair evaluation. The augmented agent could benefit from web search for out-of-domain topics, but Google Cloud does not support mixing `google_search` grounding with function-call tools in the same agent.
- **Validation cost** — The mini-eval harness runs ~21 LLM calls per agent (vs ~6 in V7). For 5 users with 4-6 agents each, this is manageable but scales linearly with agent count.
- **No trigger learning** — Triggers are static once generated. They don't update based on new conversations or evaluation feedback.
- **No cross-user transfer** — Patterns learned from one user don't benefit others, even when intents overlap.

### Future Work

- **user_1 agent recovery** — Investigate why only 1 agent survived validation. Either relax the validation threshold for users with specialized, well-separated domains, or improve agent generation quality so more agents pass the mini-eval harness.
- **False positive reduction** — Investigate questionnaire question quality for agents with high FP rates. Possible approaches: add negative-example questions ("Is this about a topic OUTSIDE the agent's domain?"), or raise the questionnaire match threshold from 0.8.
- **Re-enable web search** — When Google Cloud supports mixing `google_search` grounding with function-call tools, re-add web search to the augmented agent for out-of-domain topics.
- **Per-user embedding threshold calibration** — The infrastructure for per-user thresholds is in place (`_config.similarity_threshold` in `triggers.json`), but automatic calibration using `--calibrate-embeddings` output is not yet implemented.
- **Continuous learning** — Update swarms incrementally as new conversations accumulate, without full re-analysis.
- **Cross-user pattern sharing** — Identify universal patterns (e.g., "explain with code examples") that benefit all users.
- **Cost tracking** — Measure the additional LLM cost of multi-step mini-agents vs. the cost of extra user turns.
- **Accuracy guardrails** — Add runtime fact-checking for mini-agent outputs before delivery, particularly for domains prone to hallucination (technical/scientific content).

---

## Models Used

| Purpose | Model | Why |
|---------|-------|-----|
| Baseline + augmented agent runtime | `gemini-3-flash-preview` | Fast, cost-effective for interactive use |
| Feature extraction (Phase 3 runtime) | `gemini-2.5-flash` | Single-call structured feature extraction for trigger matching |
| Binary questionnaire eval (Phase 3 runtime) | `gemini-2.5-flash` | Evaluates per-agent yes/no questions for Stage 2 disambiguation |
| Post-generation fact-check (Phase 2) | `gemini-2.5-flash` | Scans agent prompts for fabricated claims, revises LOW-confidence ones |
| Parallel generation comparison (Phase 2) | `gemini-2.5-flash` | Selects the more grounded candidate from two parallel generations |
| Scope embedding (Phase 2 generation) | `text-embedding-005` | 768-dim embeddings for semantic similarity matching; batch-embedded at generation time |
| Message embedding (Phase 3 runtime) | `text-embedding-005` | Embeds user message for cosine similarity against pre-computed agent scopes |
| Pattern extraction (Phase 2) | `gemini-3.1-pro-preview` | Stronger reasoning for analyzing 50 conversations; requires `location="global"` |
| Swarm generation (Phase 2) | `gemini-3.1-pro-preview` | Generates high-quality Python code and generalizable triggers |
| LLM-as-judge (Phase 4) | `gemini-3.1-pro-preview` (fallback: `gemini-2.5-pro`) | Stronger reasoning for structured evaluation; retry + fallback on 429 quota errors; temperature 1.0 |
| Eval pool generation (eval) | `gemini-3.1-pro-preview` (fallback: `gemini-3-pro-preview`, `gemini-2.5-pro`) | Synthesizes diverse test cases from historic sessions |
| Eval sampler LLM review (eval) | `gemini-2.5-pro` | Confirms candidate test cases would realistically trigger the correct agent |
| User simulation (Phase 1) | `gemini-2.5-flash` | Fast role-playing for 250 conversations |

---

## Documentation Index

This project has component-level documentation in addition to this README:

| Document | Location | Description |
|----------|----------|-------------|
| **Main README** | `README.md` | This file — architecture, pipeline, results |
| **Harvest README** | `harvest/README.md` | Phase 1: conversational history generation |
| **Analyzer README** | `analyzer/README.md` | Phase 2: pattern extraction and swarm generation |
| **Baseline Agent README** | `user_assistant_agent/README.md` | Baseline agent setup and configuration |
| **Deployment Guide** | `user_assistant_agent/DEPLOYMENT.md` | Deploying the baseline agent to Google Cloud |
| **Baseline Rubric** | `evaluation_rubric.md` | 8-dimension scoring rubric (baseline) |
| **Augmented Rubric** | `evaluation_rubric_augmented.md` | 10-dimension scoring rubric (augmented) |
| **ADK Reference** | `llms.txt` | ADK/Gemini reference documentation |

---

## License

This project is for research and educational purposes.
