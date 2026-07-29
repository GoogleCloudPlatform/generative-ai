# User Assistant Agent (Baseline)

A conversational AI agent built with [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) that helps users with any question, task, or topic using conversational reasoning.

> **Note:** This is the **baseline** agent used for comparison against the augmented (swarm-enhanced) agent. Do not modify this agent — it serves as the control in evaluation.

## What the Agent Does

Users ask questions in plain language. The agent:

1. Understands the question or request
2. Answers from its training knowledge when confident
3. Asks a targeted follow-up question when the request is ambiguous

## How to Run

### Prerequisites

- Python 3.10+
- Google Cloud authentication: `gcloud auth application-default login`
- Access to the Google Cloud project configured in `.env`

### Setup

```bash
# From the project root (parent of this directory)
cd /path/to/ADK_temp

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies (if not already installed)
pip install "google-adk[vertexai]" "google-cloud-aiplatform[agent_engines,adk]" python-dotenv
```

### Run with ADK Web UI

```bash
# From the project root (NOT from inside user_assistant_agent/)
adk web
```

Open the browser UI (typically `http://localhost:8000`). Select **user_assistant** from the agent list.

### Run with ADK CLI

```bash
adk run user_assistant_agent
```

## Configuration

All configuration is in `.env`:

| Variable | Value | Purpose |
|----------|-------|---------|
| `GOOGLE_GENAI_USE_VERTEXAI` | `TRUE` | Use Google Cloud as the LLM backend |
| `GOOGLE_CLOUD_PROJECT` | `your-gcp-project-id` | Google Cloud project ID |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | Google Cloud region |

## Current Configuration

The baseline agent currently runs with `tools=[]` — no web search, no memory tools. This was done intentionally to create a fair comparison against the augmented agent, where the only differentiator is the swarm tool.

> **History:** Earlier versions included `google_search`, `PreloadMemoryTool`, `LoadMemoryTool`, and `after_agent_callback` for Memory Bank. These were removed for evaluation parity and may be re-added when Google Cloud supports mixing `google_search` grounding with function-call tools.

## File Structure

```
user_assistant_agent/
  __init__.py              # Exports root_agent for ADK discovery
  agent.py                 # Agent definition (Gemini 3 Flash Preview, tools=[])
  tools/
    __init__.py
  .env                     # Google Cloud configuration
  requirements.txt         # Python dependencies
```

## Tools

The baseline agent currently uses **no tools** (`tools=[]`). It relies solely on the LLM's training knowledge.

## Testing Scenarios

Use these to verify the agent works correctly:

| Input | Expected Behaviour |
|-------|-------------------|
| "What is photosynthesis?" | Clear factual explanation from knowledge |
| "What are the top news stories today?" | Responds from training knowledge; notes it cannot search the web for live data |
| "Tell me about Mercury" | Asks clarifying question (planet or element?) |
| "What's the capital of Japan and how many people live there?" | Answers both parts |
| "你好，澳大利亚的首都是哪里？" | Responds in Mandarin: 堪培拉 (Canberra) |
