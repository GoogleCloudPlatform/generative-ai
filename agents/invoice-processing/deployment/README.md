# Deployment Guide

Deploy an ADK agent to Agent Runtime and optionally register it on Gemini Enterprise.

**Reference:** [Google Agents CLI](https://github.com/google/agents-cli)

---

## Prerequisites

- Python 3.11+
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud` CLI)
- A GCP project with Vertex AI API enabled
- Python packages: `google-adk[vertexai]`, `python-dotenv`
- (Optional) `google-agents-cli` — required only for Gemini Enterprise registration

```bash
pip install "google-adk[vertexai]" python-dotenv
```

---

## Step 1: Authenticate and set quota project

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project <YOUR_PROJECT_ID>
```

---

## Step 2: Prepare the agent package

Agent Runtime uploads only the agent directory (the folder containing `agent.py` and `__init__.py`).

**Key requirements:**

1. **`requirements.txt`** must exist **inside the agent package directory** (not the project root). Agent Runtime uses it to install dependencies in the container.
2. **`.env`** file in the agent directory is auto-detected and deployed. Use it for runtime env vars (`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, etc.). Alternatively, use `--env_file` to point to a different file.
3. **All imports must be relative** (e.g., `from .tools.tools import ...`). Agent Runtime renames the package directory during deployment, which breaks absolute imports.
4. **Minimize the `data/` directory** — any files inside the agent package are uploaded. Remove runtime outputs (logs, cache, temp files) before deploying.
5. **Environment variable access must be lazy** — Agent Runtime sets env vars *after* module import. Any `os.getenv()` calls at module level will return `None`. Use a lazy initialization pattern (call `os.getenv()` inside a function on first use, not at import time).

### `.env` file template

Create a `.env` file in the agent package directory:

```bash
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=<YOUR_PROJECT_ID>
GOOGLE_CLOUD_LOCATION=<YOUR_REGION>
```

> A `.env.example` is provided in the agent directory. Copy it to `.env` and fill in your values.

---

## Step 3: Deploy to Agent Runtime

```bash
adk deploy agent_engine \
  --project=<YOUR_PROJECT_ID> \
  --region=<YOUR_REGION> \
  --display_name="<AGENT_DISPLAY_NAME>" \
  --description="<AGENT_DESCRIPTION>" \
  <PATH_TO_AGENT_PACKAGE>
```

On success, the CLI outputs:

```
✅ Created agent engine: projects/<PROJECT_NUMBER>/locations/<REGION>/reasoningEngines/<RESOURCE_ID>
```

**Save the `<RESOURCE_ID>`** — you need it for updates and Gemini Enterprise registration.

---

## Step 4: Update an existing deployment

To push changes without creating a new instance:

```bash
adk deploy agent_engine \
  --project=<YOUR_PROJECT_ID> \
  --region=<YOUR_REGION> \
  --agent_engine_id=<RESOURCE_ID> \
  <PATH_TO_AGENT_PACKAGE>
```

---

## Step 5: Register on Gemini Enterprise (optional)

Requires `google-agents-cli`:

```bash
pip install google-agents-cli
```

### Option A: Interactive (recommended)

```bash
agents-cli publish gemini-enterprise
```

The CLI will:
1. Auto-detect the Agent Runtime ID from `deployment_metadata.json`
2. List available Gemini Enterprise apps in your project
3. Fetch the agent's display name and description
4. Register the agent as a tool in Gemini Enterprise
5. Print a console link to view the registered agent

### Option B: Non-interactive

```bash
ID="projects/<PROJECT_NUMBER>/locations/global/collections/default_collection/engines/<GE_APP_ID>" \
AGENT_ENGINE_ID="projects/<PROJECT_NUMBER>/locations/<REGION>/reasoningEngines/<RESOURCE_ID>" \
GEMINI_DISPLAY_NAME="<AGENT_DISPLAY_NAME>" \
GEMINI_DESCRIPTION="<AGENT_DESCRIPTION>" \
agents-cli publish gemini-enterprise
```

Find your Gemini Enterprise App ID in the Google Cloud Console under Gemini Enterprise settings.

---

## Step 6: Verify

1. **Console check:** Open the Gemini Enterprise console and confirm your agent appears as an available tool
2. **Chat test:** Select the agent and send a test message
3. **Logs:** If something goes wrong, check Agent Runtime logs:

```bash
gcloud logging read \
  "resource.type=aiplatform.googleapis.com/ReasoningEngine" \
  --project=<YOUR_PROJECT_ID> \
  --limit=20 \
  --format="table(timestamp,textPayload)"
```

---

## Updating configuration post-deployment

When rules, data files, or agent instructions change:

1. Update the relevant files in the agent package
2. Re-deploy using the update command (Step 4)

No need to re-register on Gemini Enterprise — the registration points to the Agent Runtime instance, which is updated in place.

---

## Troubleshooting

### "failed to start and cannot serve traffic"

| Cause | Fix |
|-------|-----|
| Missing `requirements.txt` in agent dir | Add `requirements.txt` inside the agent package directory |
| Missing env vars | Ensure `.env` exists in the agent dir with `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` |
| Large package size | Remove runtime outputs from `data/` before deploying |
| Absolute imports | Convert all imports to relative (`.` / `..`) — Agent Runtime renames the package |
| Module-level `os.getenv()` | Defer env var reads to call time using lazy initialization |

### ADC quota warning

```bash
gcloud auth application-default set-quota-project <YOUR_PROJECT_ID>
```

---

## Further Reading

- [Google Agents CLI — Getting Started](https://github.com/google/agents-cli)
- [Google Agents CLI — Deployment](https://github.com/google/agents-cli)
- [ADK Deploy CLI Reference](https://google.github.io/adk-docs/deploy/agent-engine/)
