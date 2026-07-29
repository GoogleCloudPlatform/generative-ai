# 🎓 Tutorial: Building & Deploying Long-running AI Agents with Agent Development Kit and Agent Platform

This tutorial details a profound paradigm shift in generative AI application development: **moving away from stateless chatbots toward building reliable, time-agnostic background processes that can run for weeks.**

Stateless chat applications are excellent for short, immediate Q&A turns. However, real-world enterprise workflows (like HR onboarding, supply chain tracking, or procurement) are dominated by **"idle time"**—periods where the agent must pause execution for days or weeks, waiting for external human actions (like signing a contract) or real-world events (like hardware package deliveries).

This tutorial is styled as an **Iterative Coding Agent Playbook**. You will build a **New Hire Onboarding Coordinator Agent** by feeding high-level, intent-driven prompts incrementally to a coding agent.

---

## 🔄 Conceptual Paradigm: Architecting for Time

When designing long-running background agents, we must shift our thinking across three axes:

1. **From Stateless to Durable**: Instead of keeping conversation history in volatile memory, the agent's state must be durably serialized to a persistent database (e.g. SQLite or Cloud SQL) so it survives system restarts and idle periods.
2. **From Active Polling to Event-Driven Resumption**: Instead of keeping a thread blocked or actively polling APIs for weeks, the agent must enter a dormant "paused" state. It is awakened programmatically only when an external webhook event triggers a resume event.
3. **From Single-Agent Monoliths to Multi-Agent Delegation**: Long-running processes involve disparate tasks. Rather than forcing a single coordinator to hold all tool definitions, we delegate specialized sub-workflows (like IT provisioning) to isolated subagents, handing control back when finished.

---

## 🏗️ Step-by-Step Build Playbook

Before we begin, ensure you have the **Agents CLI** (`agents-cli`) installed. This is the official command-line interface for the **Gemini Enterprise Agent Platform**, providing standard commands to scaffold projects, run local playgrounds, perform golden evaluations, and deploy reasoning engines.

Install it globally using the `uv` tool manager:
```bash
uv tool install google-agents-cli
```

Follow these 6 structured phases to build the time-agnostic onboarding coordinator using iterative agent prompts.

---

### Phase 1: The Foundation Scaffold

We begin by bootstrapping our project structure and preparing it for persistent execution rather than simple chat.

> ### 🤖 Coding Agent Prompt 1: The Foundation Scaffold
>
> "Scaffold a new ADK agent project named 'onboarding-agent' in prototype mode. This is a long-running background process that should survive infrastructure restarts, so please ensure persistent session and memory bank settings are wired up from the start."

#### Key Scaffold Outcomes:
- A standard ADK project structure is initialized.
- Volatile session parameters are cleared to prepare for database storage.

---

### Phase 2: Grounding with a Strict State Machine

Most chatbot tutorials rely on dumping massive conversation history JSON blobs into a vector database to "remember" past turns. However, over multi-day workflows, this unstructured approach introduces severe prompt context pollution, high token costs, and reasoning hallucinations.

To build reliable background agents, we design a **durable, lightweight agent memory schema**. By grounding the coordinator in a strict enum-based state machine, we guarantee the agent maintains its logical reasoning chain across weeks of delay, without relying on raw chat logs.

> ### 🤖 Coding Agent Prompt 2: Grounding with a State Schema
>
> "We need to implement a strict state machine to ground our onboarding coordinator. Define an enum schema with steps: `START`, `WELCOME_SENT`, `DOCUMENTS_SIGNED`, `IT_PROVISIONED`, `HARDWARE_DELIVERED`, and `COMPLETED`, to track and enforce sequential task completion."

#### Resulting Code ([app/state_schema.py](app/state_schema.py)):
```python
from enum import Enum

class OnboardingStep(str, Enum):
    START = "START"
    WELCOME_SENT = "WELCOME_SENT"
    DOCUMENTS_SIGNED = "DOCUMENTS_SIGNED"
    IT_PROVISIONED = "IT_PROVISIONED"
    HARDWARE_DELIVERED = "HARDWARE_DELIVERED"
    COMPLETED = "COMPLETED"
```

---

### Phase 3: Multi-Agent IT Provisioning Delegation

Rather than stuffing all IT and HR tools into a single coordinator agent, we instantiate a specialized subagent responsible solely for software account setups.

> ### 🤖 Coding Agent Prompt 3: Multi-Agent Delegation Setup
>
> "Rather than having our main onboarding coordinator invoke provisioning tools directly, let's delegate IT setup. Add a specialized subagent 'it_agent' to handle software account provisioning, register it under the main coordinator, and update the coordinator's instructions to delegate to it when documents are signed."

#### Resulting Code Segment ([app/agent.py](app/agent.py)):
```python
from google.adk.agents import Agent
from app.tools import provision_software_accounts

it_agent = Agent(
    name="it_agent",
    instructions="""You are the IT Provisioning Assistant.
    Your sole responsibility is to provision corporate accounts.
    When asked, collect the desired username prefix and call the 'provision_software_accounts' tool.
    Once complete, hand control back to the coordinator immediately.""",
    tools=[provision_software_accounts],
    model="gemini-3.5-flash"
)
```

---

### Phase 4: Durable Database-Backed Session Storage

In a serverless containerized environment (such as Cloud Run), containers frequently cold-start, scale down to zero when idle, or restart unexpectedly. Furthermore, external API tools might hit transient rate limits. If our agent's state lives in volatile container memory, all in-flight onboarding runs are permanently lost during these events.

To build resilient multi-day background processes, we implement a strict **Checkpoint-and-Resume loop**. By writing our agent's session checkpoints to a persistent database (such as SQLite locally or Cloud SQL in production), the agent can survive container restarts, and failed operations can trigger safe retries without losing or corrupting the onboarding state.

> ### 🤖 Coding Agent Prompt 4: Persistent SQL Session Setup
>
> "To allow our onboarding sessions to survive long delays and server restarts, transition our session storage from volatile in-memory to persistent SQLite storage (sqlite+aiosqlite:///sessions.db) in our FastAPI application."

#### Resulting Code Segment ([app/fast_api_app.py](app/fast_api_app.py)):
```python
from google.adk.sessions import DatabaseSessionService

# Durable SQLite persistence
session_service_uri = "sqlite+aiosqlite:///sessions.db"
db_session_service = DatabaseSessionService(db_url=session_service_uri)

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    session_service_uri=session_service_uri,
    otel_to_cloud=True,
)
```

---

### Phase 5: Event-Driven Resumption & Structured JSON Logging

The most challenging aspect of long-running workflows is managing **"idle time"**—the long gaps when the agent goes dormant to wait for human approvals or slow physical actions (like document signatures or shipping packages).

We handle this by **serializing the agent's working memory** at the moment of the pause, storing both the full conversation thread and our custom step variables in SQLite. When the external signature event triggers the webhook, the resume handler **hydrates the working memory** seamlessly. This ensures the LLM restores its complete context and picks up the logical reasoning chain *exactly* where it left off, without any memory dropouts or hallucinated deviations.

> ### 🤖 Coding Agent Prompt 5: Webhooks & Ambient Wake-up Setup
>
> "Expose webhook endpoints for contract signature and hardware delivery events on our FastAPI server. Create a resume handler that automatically hydrates the matching session state, transitions the onboarding step, and wakes up the agent programmatically using `runner.run_async` to execute the next step ambiently. Include structured JSON logging for all key webhook events."

#### Resulting Webhook Code Segment ([app/fast_api_app.py](app/fast_api_app.py)):
```python
@app.post("/webhooks/document_signed")
async def trigger_document_signed_webhook(payload: WebhookPayload):
    await resume_handler.receive_signed_documents_callback(
        user_id=payload.user_id,
        session_id=payload.session_id
    )
    return {"status": "success", "message": "Document signature processed, agent resumed."}
```

#### Resulting Resume Handler Segment ([app/resume_handler.py](app/resume_handler.py)):
```python
async for event in self.runner.run_async(
    user_id=user_id,
    session_id=session_id,
    new_message=types.Content(
        role="user",
        parts=[types.Part.from_text("Resume onboarding: Contract has been signed.")]
    )
):
    self._log_structured(
        severity="INFO",
        message=f"Wake-up execution event: {event}",
        event="runner_event",
        session_id=session_id
    )
```

---

### Phase 6: Simulating week-long "Idle Time" delays (Evals)

How do we test an onboarding flow that spans days? We write multi-turn Golden simulation tests that mock delays and webhook triggers.

> ### 🤖 Coding Agent Prompt 6: Golden Case Delay Simulation
>
> "Use the agents-cli evaluation skills to generate an eval set for our onboarding workflow. Create test trajectories that specifically simulate 'idle time'. I need a test case that mocks a 48-hour delay for IT hardware provisioning, and verifies that the agent resumes and successfully routes the final schedule without dropping the new hire's original context."

#### Verifying Evaluations:
Execute the direct ADK virtualenv script to run your delay simulations locally bypassing transient packaging registry issues:
```bash
.venv/bin/adk eval ./app tests/eval/evalsets/idle_time_delay_eval.json --config_file_path tests/eval/eval_config.json
```

---

## 🚀 Production Deployment Setup

When evaluations are green, elevate your project target to **Gemini Enterprise Agent Platform (Agent Runtime)**:

> ### 🤖 Coding Agent Prompt 7: Managed Platform Scaffolding
>
> "We are ready to deploy. Use `agents-cli scaffold enhance` to target Gemini Enterprise Agent Runtime (Agent Engine). Scaffold the Reasoning Engine app wrapper, and ensure Cloud Trace integration is wired up so we can monitor our pause-and-resume latencies in production."

This command:
- Prepares the project to run on Google Cloud Agent Runtime.
- Natively handles session persistence directly in the cloud.
- Enables **Cloud Trace** out-of-the-box by default.

---

## 🎯 Summary of Key Learnings
- **Chatbots are a subset**: Background processes are the future of enterprise AI automation.
- **Grounded state machines**: Enums and persistent databases protect your coordinator from losing tracks during days of inactivity.
- **Mocking time**: ADK evaluations are powerful tools to simulate multi-day delays instantly in continuous integration pipelines.
