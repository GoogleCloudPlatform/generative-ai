# Deployment Guide — User Assistant Agent

Deploy to Agent Engine and optionally register on Gemini Enterprise.

---

## Prerequisites

- A Google Cloud project with Google Cloud enabled
- Python packages: `google-adk[vertexai]`, `python-dotenv`
- (Optional) `agent-starter-pack` for Gemini Enterprise registration

---

## Step 1: Create a gcloud configuration

```bash
# Create a named gcloud config
gcloud config configurations create my-config

# Set the project
gcloud config set project your-gcp-project-id

# Set your account
gcloud config set account your-email@example.com

# Verify
gcloud config configurations list
```

Activate this config:

```bash
export CLOUDSDK_ACTIVE_CONFIG_NAME=my-config
```

---

## Step 2: Authenticate

### 2a. Login to gcloud

```bash
gcloud auth login
```

### 2b. Create Application Default Credentials (ADC)

```bash
gcloud auth application-default login
```

### 2c. Enable required APIs

```bash
gcloud services enable aiplatform.googleapis.com --project=your-gcp-project-id
gcloud services enable cloudresourcemanager.googleapis.com --project=your-gcp-project-id
```

---

## Step 3: Install dependencies

```bash
pip install "google-adk[vertexai]" python-dotenv
```

---

## Step 4: Update .env

Edit `user_assistant_agent/.env` with your project details:

```
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

---

## Step 5: Deploy to Agent Engine

```bash
# From the project root
adk deploy agent_engine \
  --project=your-gcp-project-id \
  --region=us-central1 \
  --display_name="User Assistant Agent" \
  --description="General-purpose AI assistant" \
  user_assistant_agent
```

**On success**, the CLI outputs a resource ID like:
```
Agent deployed successfully. Resource ID: 1234567890
```

**Save this ID** — you'll need it for registration and updates.

### Updating an existing deployment

```bash
adk deploy agent_engine \
  --project=your-gcp-project-id \
  --region=us-central1 \
  --agent_engine_id=<RESOURCE_ID> \
  user_assistant_agent
```

---

## Step 6: Register on Gemini Enterprise (optional)

### Option A: Interactive (recommended)

```bash
agent-starter-pack register-gemini-enterprise
```

### Option B: Non-interactive

```bash
ID="projects/YOUR_PROJECT_NUMBER/locations/global/collections/default_collection/engines/YOUR_APP_ID" \
AGENT_ENGINE_ID="projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID" \
GEMINI_DISPLAY_NAME="User Assistant Agent" \
GEMINI_DESCRIPTION="General-purpose AI assistant with web search" \
agent-starter-pack register-gemini-enterprise
```

---

## Step 7: Verify

1. **Console check:** Confirm the agent appears in the Gemini Enterprise console
2. **Chat test:** Try: "What are the latest news headlines?"
3. **Expected behaviour:** The agent should use web search and provide a sourced summary

---

## Quick reference: environment setup per session

```bash
export CLOUDSDK_ACTIVE_CONFIG_NAME=my-config
# If using a saved ADC file:
# export GOOGLE_APPLICATION_CREDENTIALS=$HOME/.config/gcloud/adc-my-config.json
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `Permission denied` on deploy | Verify your account has Google Cloud User / Editor roles |
| Agent not appearing in Gemini Enterprise | Re-run `register-gemini-enterprise` |
| Region mismatch | Agent Engine and Gemini Enterprise app must be in compatible regions |
| ADC expired | Re-run: `gcloud auth application-default login` |
