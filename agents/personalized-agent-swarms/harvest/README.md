# Harvest — Conversational History Generation

Generates simulated user-assistant conversations for building personalized mini-agent swarms.

## How It Works

1. Loads user personas from `user_profiles/profiles.json`
2. For each user and scenario, creates a simulated conversation:
   - Turn 1: Uses the scenario's `opening_message`
   - Turns 2+: A `UserAgent` (LLM-powered) generates follow-ups based on the persona and strategy
   - The baseline `user_assistant_agent` responds to each turn
3. Saves full conversation logs to `history/{user_id}/session_{NNN}.json`

**Key files:**
- `orchestrator.py` — Drives the conversation loop; also exports `_BASELINE_INSTRUCTION` (shared with the test harness)
- `user_agent.py` — Simulated user personas with follow-up strategies (deep_dive, clarify, pivot, correct)

## Usage

```bash
# Prerequisites
source .venv/bin/activate
python user_profiles/generate_profiles.py  # generate profiles first

# Full harvest (5 users x 50 scenarios = 250 sessions)
python harvest/orchestrator.py

# Test run (one user, 5 scenarios)
python harvest/orchestrator.py --user user_1 --limit 5 --verbose

# Resume interrupted harvest
python harvest/orchestrator.py --resume
```

## Output

Each session is saved as `history/{user_id}/session_{NNN}.json` with this structure:

```json
{
  "user_id": "user_1",
  "scenario_id": "user_1_scenario_001",
  "intent": "debug_python_code",
  "turns": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "turn_count": 3,
  "timestamp": "2026-04-17T10:00:00Z"
}
```
