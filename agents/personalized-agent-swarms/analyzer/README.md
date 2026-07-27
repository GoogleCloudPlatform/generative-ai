# Analyzer — Pattern Extraction & Swarm Generation

Processes conversational history to extract recurring intent patterns and generate personalized mini-agent swarms.

## How It Works

1. Loads session logs from `history/{user_id}/`
2. Batches sessions (10 at a time) and sends them to Gemini 3.1 Pro for pattern extraction
3. Merges and deduplicates patterns across batches
4. Filters to patterns appearing in >= 3 sessions
5. Separates task patterns (what user wants) from behavioral patterns (how user communicates)
6. Behavioral patterns → `user_style.json` (shared style profile)
7. For each task pattern, generates:
   - A trigger definition (`triggers.json`) with structured attribute rules
   - A Python mini-agent file (`agents/{pattern_name}.py`)
   - Scope embeddings (768-dim, `text-embedding-005`) for semantic matching
8. Critic/revision pass validates each agent against history sessions (up to 3 rounds)
9. Non-parametric quality ranking keeps all agents scoring >= 25/50 (5-dimension rubric, hard cap 30)
10. Coverage validation checks for gaps after ranking and widens surviving agents

## Key Components

- `analyze_history.py` — Main entry point
- `pattern_extractor.py` — LLM-based pattern clustering
- `swarm_generator.py` — Generates mini-agent .py files, triggers, embeddings, runs critic/ranking
- `trigger_schema.py` — Feature schema, extraction prompts, soft penalty matching logic, rule validation
- `llm_util.py` — Retry + model fallback wrapper for Google Cloud calls

## Matching Logic (trigger_schema.py)

Domain and task_type mismatches apply **soft scoring penalties** (0.15 / 0.10) to embedding similarity instead of binary rejection. This allows cross-domain requests to match when semantic similarity is high. Keyword-based matching (`require_any_keyword`, `exclude_keywords`) has been removed — pure semantic matching only.

## Usage

```bash
source .venv/bin/activate

# Analyze all users
python analyzer/analyze_history.py

# One user, dry run (show patterns only)
python analyzer/analyze_history.py --user user_1 --dry-run --verbose

# Full generation for one user
python analyzer/analyze_history.py --user user_1

# Skip critic pass (faster)
python analyzer/analyze_history.py --user user_1 --skip-critic
```

## Output

```
swarms/{user_id}/
├── manifest.json          # Index of all agents + metadata + critic/ranking results
├── triggers.json          # Trigger rules + scope embeddings (768-dim) + _config
├── user_style.json        # Behavioral pattern profile
└── agents/
    ├── pattern_name_1.py  # Mini-agent with async execute() function
    └── pattern_name_2.py  # (quality-based count, typically 5-10)
```
