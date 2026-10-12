# Invoice Processing

A unified ADK agent for document processing that combines an end-to-end inference pipeline with an interactive learning system for continuous improvement -- all in a single self-contained agent.

**Current reference implementation:** Invoice Processing.

## Overview & Functionalities

### Agent Details

| Property | Value |
|----------|-------|
| **Interaction Type** | Conversational |
| **Complexity** | Advanced |
| **Agent Type** | Single Agent (dual-mode) |
| **Vertical** | Finance / Document Processing |
| **ADK Pattern** | `LlmAgent` + 18 `FunctionTools` |
| **Model** | gemini-3.5-flash |
| **Framework** | [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) |


### Key Features

| Component | Description |
|-----------|-------------|
| **Dual-Mode Prompt** | Single agent supports both Inference and Learning modes, selectable at session start with seamless switching |
| **9-Agent Acting Pipeline** | Classification, extraction, 4-phase validation, transformation, output generation, audit logging |
| **3-Layer Investigation** | Deterministic checks (Layer 1), LLM-powered rule discovery with SHA-256 caching (Layer 2), per-group ultra-conservative validation (Layer 3) |
| **ALF Correction Engine** | Collect-Plan-Execute pipeline: deterministic condition matching (24 operators), scope-based mutual exclusion, hybrid execution (LLM + deterministic) |
| **Impact Assessment** | Evaluates proposed rules against all existing cases to detect collateral matches before committing |
| **Rule Management** | Schema validation, conflict detection, backup on write, ID auto-assignment |
| **Session Logging** | Full audit trail of SME interactions, rule proposals, and approvals |
| **Schema-Driven Eval** | Two-layer evaluation: deterministic field comparison + optional LLM-as-judge |
| **Domain-Agnostic Config** | All domain knowledge in `master_data.yaml` -- swap to adapt to any document type |

### Design Principles

- **Black box acting agent** -- the acting agent is never modified; all evolution happens downstream (ALF, learning)
- **Self-contained agent** -- all data, libraries, and test cases live inside the agent package
- **Layered corrections** -- deterministic rules first, LLM only when needed, human approval always
- **Configuration over code** -- domain knowledge lives in `master_data.yaml`, not in source code
- **Human governance** -- every correction rule requires SME review and approval
- **Backward compatible** -- all components fall back to hardcoded invoice defaults when no master data is available

### Tools

**Inference tools (2):**
- `list_inference_cases()` -- discover available cases
- `run_inference(case_id, skip_investigation="true"|"false")` -- run Acting -> Investigation -> ALF pipeline (Investigation is optional)

**Learning tools (16):**
- `list_cases()`, `load_case(case_id)` -- browse and review processed cases
- `discover_safe_rule(case_id, sme_feedback)` -- generate rule with automatic safety loop (validate -> assess impact -> auto-tighten)
- `revise_safe_rule(case_id, rule_json, sme_feedback)` -- revise a rule with the same safety loop
- `build_rule_discovery_context(case_id, sme_feedback)` -- build LLM context for manual rule generation
- `build_rule_revision_context(case_id, rule_json, feedback, impact)` -- build context for manual revision
- `validate_rule(rule_json)`, `check_conflicts(rule_json)` -- schema and conflict checks
- `assess_impact(conditions_json, target_case_id)` -- cross-case impact analysis
- `write_rule(rule_json, mode)`, `delete_rule(rule_id)` -- persist/remove rules in `rule_base.json`
- `get_existing_rules()`, `get_existing_scopes()`, `get_next_rule_id()` -- rule base queries
- `format_rule_display(rule_json)` -- human-readable rule formatting
- `log_session_event(event_type, data_json)`, `save_session()` -- audit logging

### Example Interaction: Inference Mode

```
Agent: Welcome to Invoice Processing! Which mode would you like to work in?
       (1) Inference -- process cases, or (2) Learning -- review & create rules?

You:   1

Agent: Great, we're in Inference mode.

You:   Run case_002 and case_005, skip the critic

Agent: Inference pipeline completed for case_002:

       Stage 1 -- Acting Agent: ACCEPT (Pending Payment)
         Vendor: Precision Tech Co Pty Ltd | Invoice: INV-00002 ($555.50 AUD)

       Investigation: SKIPPED

       Stage 2 -- ALF: 0 rules evaluated -- output unchanged.

       Final output: data/agent_output/case_002/

Agent: Inference pipeline completed for case_005:

       Stage 1 -- Acting Agent: REJECT
         Vendor: QuickFix HVAC Repairs | Invoice: INV-00005 ($1,069.32 AUD)
         Rejection Phase: Phase 4 (Step 4.3: Labour hours within authorization)
         Rejection Reason: Invoice does not match work authorization
           (Invoice: 2.5h, WAF authorized hours: 0)

       Investigation: SKIPPED

       Stage 2 -- ALF: 0 rules evaluated -- output unchanged.

       Final output: data/agent_output/case_005/
```

### Example Interaction: Learning Mode

The SME reviews case_005. The acting agent rejected at Phase 4 Step 4.3 because the invoice bills 2.5 labour hours but no WAF was submitted to authorize them. The calculations are correct (totals match, GST is 10%) -- this is a work authorization issue, not a calculation error. The SME identifies this as a **policy exception**: emergency maintenance jobs under $2,000 are exempt from WAF requirements per updated procurement policy.

```
You:   Switch to learning

Agent: Switched to Learning mode.

You:   Load case_005

Agent: Case case_005 loaded:

       Decision: REJECT
       Rejection reason: 'Invoice does not match work authorization'
       Failed at: Phase 4, Step 4.3: Labour hours within authorization
         Evidence: Invoice: 2.5h, WAF authorized hours: 0

       Vendor: QuickFix HVAC Repairs (ABN: 51824753556)
       Invoice: INV-00005 ($1,069.32 AUD), dated 2026-02-11
       Line Items: Gasket and seal kit (3 x $219.87) + Technician labour (2.5h x $125)
       Subtotal: $972.11 | GST: $97.21 | Total: $1,069.32
       Has WAF: No (waf_count: 0)

       Validation phases:
         Phase 1 (Intake): CONTINUE (4/4 passed)
         Phase 2 (PO/Invoice): CONTINUE (1/1 passed)
         Phase 3 (Status/Date): CONTINUE (2/2 passed)
         Phase 4 (Totals/EWAF): REJECT (2/3 passed)
           FAILED Step 4.3: Labour hours within authorization

You:   This is an emergency HVAC repair. Our updated procurement policy
       exempts maintenance jobs under $2,000 from the WAF requirement.
       Create a rule to accept these cases.

Agent: Generating rule via discover_safe_rule...

       === Proposed Rule: ALF-001 ===
       Name: WAF Exemption for Emergency Maintenance Under $2,000
       Scope: waf_exemption | Priority: 50

       Conditions:
         1. decision_phase4 equals "REJECT"
         2. phase4.rejection_template contains "work authorization"
         3. invoice.total_amount less_than 2000

       Actions:
         1. set_field
            Invoice Processing.Invoice Status = "Pending Payment"
            Invoice Processing.Rejection Reason = ""
            Invoice Processing.Rejection Phase = ""

       Metadata:
         Root cause: Policy exception -- updated procurement policy
           not yet reflected in rules book

       Impact Assessment:
         Case case_005: MATCH (target)
         4 other cases: NO MATCH (safe)

       Would you like to approve, revise, or discard?

You:   Add a condition for maintenance service categories only.

Agent: Revising via revise_safe_rule...

       Revised Conditions:
         1. decision_phase4 equals "REJECT"
         2. phase4.rejection_template contains "work authorization"
         3. invoice.total_amount less_than 2000
         4. invoice.service_category in ["HVAC", "ELECTRICAL", "PLUMBING"]

       Impact: case_005 MATCH (HVAC, $1,069.32), 4 others safe.

You:   Approve

Agent: Rule ALF-001 written. Total rules: 1.
```

ALF rules handle **exceptions not covered by the rules book** -- not bugs in the acting agent. They use low-effort deterministic actions (`set_field`) to patch output fields directly without re-running pipeline stages.

---

## Architecture

![Architecture Diagram](agent_pattern.webp)

The diagram above illustrates the three-zone architecture of the Invoice Processing agent:

- **Zone 1 -- The Constitution Architecture:** The Reconstructed Rules Book serves as the agent's "constitution" -- the single source of truth and transparency. It governs how both the Acting Agent and the Critic Agent (Investigation) behave, ensuring all decisions are traceable back to documented rules.

- **Zone 2 -- The Runtime Inference Pipeline:** An input invoice flows through three sequential stages. First, the **Acting Agent** processes it through a 4-step internal pipeline (Classify, Extract, Validate, Reason). Next, the **Critic Agent** (Investigation) audits the Acting Agent's output against the constitution, with the ability to STOP or allow continuation. Finally, the **ALF engine** (Adaptive Learning Framework) checks its Rule Base for matching correction rules and applies a Collect-Plan-Execute pipeline to produce the final approved output.

- **Zone 3 -- The Learning & Evolution Loop:** When a Human Expert (SME) flags an error in the final output, they provide feedback to the **Rule Learning Agent (RLA)**. The RLA generates a new exception rule that is written into the ALF Rule Base. On subsequent inference runs, the ALF engine automatically applies this correction. Over time, a Periodic System Review promotes frequent exception rules into permanent changes to the Acting Agent itself (green arrow), closing the evolution loop.

```
                 exemplary_data/
                 (input PDFs + ground truth)
                       |
                       v
         +-------------------------------+
         |          Invoice Processing   |
         |    (single LlmAgent, 18 tools)|
         +-------------------------------+
         |                               |
    INFERENCE MODE              LEARNING MODE
         |                               |
    run_inference()          load_case() + SME feedback
         |                               |
    +----+----+----+          discover_safe_rule()
    |    |    |    |                      |
    v    v    v    v          generate -> validate -> assess -> write
  [Act][Inv][ALF] |                      |
   |    |    |    |              rule_base.json
   |    |    |    |              (new/updated rules)
   v    v    v    v                      |
  data/agent_output/          +----------+
  data/alf_output/            |
                              v
                         Next inference run
                         picks up new rules

  ACTING PIPELINE (9 agents):
  PDF -> Classify -> Extract -> Phase1 -> Phase2 -> Phase3 -> Phase4
      -> Transform -> Output -> Audit

  INVESTIGATION (3 layers):
  Layer 1: Deterministic (data source, bypass, tolerance)
  Layer 2: LLM rule discovery (cached by SHA-256)
  Layer 3: Per-group validation (ultra-conservative LLM)

  ALF ENGINE (Collect-Plan-Execute):
  Collect: Evaluate rules deterministically (24 operators, scope exclusion)
  Plan:    Categorize actions into 3 tiers
  Execute: Tier 1 LLM pipeline continuation | Tier 2 LLM field patch | Tier 3 deterministic
```

### Folder Structure

```
invoice-processing/
├── invoice_processing/                      # Python package (fully self-contained)
│   ├── __init__.py                 # Exports root_agent
│   ├── agent.py                    # LlmAgent + run_inference pipeline + root_agent
│   ├── prompt.py                   # Dual-mode instruction prompt
│   ├── tools/
│   │   └── tools.py               # 18 FunctionTools (inference + learning)
│   ├── shared_libraries/
│   │   ├── master_data_loader.py   # Domain config loader
│   │   ├── invoice_master_data.yaml
│   │   ├── alf_engine.py           # ALF correction engine (87 KB)
│   │   ├── acting/
│   │   │   └── general_invoice_agent.py   # 9-agent pipeline (61 KB)
│   │   └── investigation/
│   │       └── investigate_agent_reconst.py  # 3-layer validation
│   ├── core/                       # Learning logic
│   │   ├── config.py               # Central path/LLM configuration
│   │   ├── case_loader.py          # Load processed case artifacts
│   │   ├── impact_assessor.py      # Rule impact analysis across all cases
│   │   ├── rule_writer.py          # Rule validation, conflict detection, persistence
│   │   ├── rule_discoverer.py      # LLM-driven rule generation
│   │   ├── safe_rule_orchestrator.py # Programmatic safety loop for rule discovery
│   │   ├── session_logger.py       # Audit logging
│   │   └── prompts.py             # LLM prompt templates for rule discovery
│   ├── data/                       # Runtime data (inside agent package)
│   │   ├── agent_output/           # Per-case processing artifacts
│   │   ├── alf_output/             # ALF-corrected outputs
│   │   ├── investigation_output/   # Investigation reports
│   │   ├── eval_results/           # Evaluation results
│   │   ├── learning_sessions/      # Session logs
│   │   ├── rule_base.json          # ALF correction rules
│   │   ├── reconstructed_rules_book.md
│   │   └── rule_discovery_cache.json
│   ├── exemplary_data/             # Test cases with PDFs and ground truth
│   │   └── case_001/ ... case_005/
│   └── sub_agents/
├── deployment/
├── eval/
│   ├── eval.py                     # Schema-driven ground truth evaluation
│   └── compare_postprocessing.py   # ALF before/after diff
├── tests/
├── pyproject.toml
├── .env.example
└── README.md                       # This file
```

---

## Setup & Execution

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management
- Google Cloud project with Agent Platform (Vertex AI) API enabled
- [Google ADK](https://google.github.io/adk-docs/)
- Google Cloud authentication configured

### Installation

```bash
# Navigate to the agent directory
cd agents/invoice-processing

# Install dependencies using uv
uv sync

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your Google Cloud project details:
#   GOOGLE_CLOUD_PROJECT=your-gcp-project-id
#   GOOGLE_CLOUD_LOCATION=us-central1

# Authenticate with Google Cloud
gcloud auth application-default login
```

### Environment Variables

See [`.env.example`](.env.example) for the full list. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLOUD_PROJECT` | (required) | Google Cloud project ID |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | Google Cloud region |
| `MODEL_NAME` | `gemini-3.5-flash` | Model for the ADK agent |
| `GEMINI_PRO_MODEL` | `gemini-3.5-pro` | Model for ALF pipeline continuation and investigation |
| `API_CALL_DELAY_SECONDS` | `1.0` | Rate limiting between API calls |

### Running the Agent

```bash
# Launch via ADK web UI (from the recipe directory)
adk web invoice_processing

# Open http://127.0.0.1:8000 in your browser
# Select "invoice_processing" from the app list
```

The agent will greet you with a mode selection prompt. Choose Inference to process cases or Learning to review and create rules.

### Running via CLI

```bash
# ADK CLI mode (non-interactive, run from agents directory)
adk run invoice_processing
```

---

## Customization & Extension

### Modifying the Agent Flow

| What to change | Where |
|----------------|-------|
| Agent instructions and conversation behavior | [`invoice_processing/prompt.py`](invoice_processing/prompt.py) -- edit `INVOICE_PROCESSING_INSTRUCTION` |
| Pipeline stages, gating logic, stage ordering | [`invoice_processing/agent.py`](invoice_processing/agent.py) -- edit `run_inference()` |
| Which tools are available to the agent | [`invoice_processing/agent.py`](invoice_processing/agent.py) -- edit the `tools=[]` list in `root_agent` |
| Model selection | [`invoice_processing/agent.py`](invoice_processing/agent.py) -- change `model=` parameter in `root_agent` |

### Adding New Tools

1. Add your function to [`invoice_processing/tools/tools.py`](invoice_processing/tools/tools.py):
   ```python
   def my_new_tool(param: str) -> dict:
       """Description shown to the LLM. Args documented here."""
       # your logic
       return {"result": "..."}
   ```

2. Import and register it in [`invoice_processing/agent.py`](invoice_processing/agent.py):
   ```python
   from invoice_processing.tools.tools import my_new_tool

   root_agent = LlmAgent(
       ...
       tools=[..., my_new_tool],
   )
   ```

3. Update the prompt in [`invoice_processing/prompt.py`](invoice_processing/prompt.py) to tell the agent when and how to use the new tool.

### Changing Data Sources

| What to change | How |
|----------------|-----|
| **Domain configuration** | Replace [`shared_libraries/invoice_master_data.yaml`](invoice_processing/shared_libraries/invoice_master_data.yaml) with your domain's YAML. The `MasterData` class provides typed accessors for 11 sections: document types, extraction schemas, taxonomies, validation pipeline, output schema, eval comparison groups, and more. |
| **Validation rules** | Edit [`data/reconstructed_rules_book.md`](invoice_processing/data/reconstructed_rules_book.md) -- the "constitution" that the investigation layer validates against. |
| **ALF correction rules** | Edit [`data/rule_base.json`](invoice_processing/data/rule_base.json) directly, or use Learning mode to create rules interactively. |
| **Test cases** | Add new case folders to [`exemplary_data/`](invoice_processing/exemplary_data/) with PDFs and optional ground truth `Postprocessing_Data.json`. |

### Adapting to a New Document Domain

1. Create a new `your_domain_master_data.yaml` following the schema in `invoice_master_data.yaml`
2. Replace the acting agent in `shared_libraries/acting/` with your domain's processing pipeline
3. Update `data/reconstructed_rules_book.md` with your domain's validation rules
4. Add test cases to `exemplary_data/`
5. All framework components (ALF, investigation, eval) automatically adapt via the master data configuration -- no code changes needed

---

## Evaluation

The evaluation framework lives in [`eval/`](eval/) and provides schema-driven assessment of agent output quality.

### Methodology

**Two-layer evaluation** (implemented in [`eval/eval.py`](eval/eval.py)):

| Layer | Type | Cost | Description |
|-------|------|------|-------------|
| **Layer 1: Deterministic** | Field-by-field comparison | Free | Compares agent output against ground truth using comparison groups defined in master data. Instant, reproducible, zero cost. |
| **Layer 2: LLM-as-Judge** | Holistic alignment | ~1 API call/case | Single Gemini call per case producing an overall alignment verdict. Optional (`--skip-llm` to disable). |

### Metrics

- **Field-level match rates** per comparison group (header fields, line items, totals, tax, decision)
- **Decision alignment**: does the agent's ACCEPT/REJECT match ground truth?
- **Financial tolerance**: configurable threshold for numeric comparisons (default: $0.02)
- **LLM verdicts** (when enabled):
  - `ALIGNED` -- output matches ground truth in all material respects
  - `PARTIALLY_ALIGNED` -- correct decision but some field differences
  - `NOT_ALIGNED` -- wrong decision or critical data errors

### Running Evaluations

```bash
# Paths are resolved relative to the invoice_processing package, so
# "exemplary_data" and "data/agent_output" resolve inside it.

# Full evaluation (deterministic + LLM)
uv run eval/eval.py \
    --ground-truth exemplary_data \
    --agent-output data/agent_output

# Deterministic only (no LLM, no cost)
uv run eval/eval.py \
    --ground-truth exemplary_data \
    --agent-output data/agent_output \
    --skip-llm

# Single case evaluation
uv run eval/eval.py \
    --ground-truth exemplary_data \
    --agent-output data/agent_output \
    --case case_001

# Custom financial tolerance
uv run eval/eval.py \
    --ground-truth exemplary_data \
    --agent-output data/agent_output \
    --tolerance 0.05

# Compare original vs ALF-revised output (before/after diff)
uv run eval/compare_postprocessing.py
```

Results are saved to `invoice_processing/data/eval_results/`.

---

## Deployment

To deploy Invoice Processing to a cloud environment, follow the [ADK Samples Integration](https://github.com/google/agents-cli) instructions to deploy via Google Agents CLI.

See [`deployment/README.md`](deployment/README.md) for details.

---

## Production: GCS Integration

In local development, all data lives inside the agent package (`invoice_processing/data/` and `invoice_processing/exemplary_data/`). For production deployment, these directories should be replaced with Google Cloud Storage (GCS) buckets so that:

- **Incoming invoice cases** are read from a bucket where upstream systems or users upload PDFs
- **Intermediate and final outputs** are written to a bucket for downstream consumption
- **Rule base and rules book** are stored in a bucket accessible to SMEs for review and editing

### Local vs Production Data Mapping

| Local Path | GCS Bucket Path | Direction | Description |
|-----------|-----------------|-----------|-------------|
| `invoice_processing/exemplary_data/` | `gs://{BUCKET}/incoming_cases/` | Read | Invoice PDFs and supporting documents uploaded by users or upstream systems |
| `invoice_processing/data/agent_output/` | `gs://{BUCKET}/agent_output/` | Write | Per-case intermediate artifacts (classification, extraction, validation, etc.) |
| `invoice_processing/data/alf_output/` | `gs://{BUCKET}/alf_output/` | Write | ALF-corrected final outputs |
| `invoice_processing/data/investigation_output/` | `gs://{BUCKET}/investigation_output/` | Write | Investigation compliance reports |
| `invoice_processing/data/eval_results/` | `gs://{BUCKET}/eval_results/` | Write | Evaluation results |
| `invoice_processing/data/learning_sessions/` | `gs://{BUCKET}/learning_sessions/` | Write | SME session logs |
| `invoice_processing/data/rule_base.json` | `gs://{BUCKET}/config/rule_base.json` | Read/Write | ALF correction rules (user-facing) |
| `invoice_processing/data/reconstructed_rules_book.md` | `gs://{BUCKET}/config/reconstructed_rules_book.md` | Read | Validation rules constitution (user-facing) |
| `invoice_processing/data/rule_discovery_cache.json` | `gs://{BUCKET}/config/rule_discovery_cache.json` | Read/Write | Cached rule discovery results |

### Recommended Bucket Structure

```
gs://your-invoice-processing-bucket/
├── incoming_cases/                    # Upload invoices here
│   ├── case_001/
│   │   ├── invoice.pdf
│   │   └── waf.pdf
│   ├── case_002/
│   │   └── invoice.pdf
│   └── .../
│
├── agent_output/                      # Agent writes intermediate artifacts here
│   ├── case_001/
│   │   ├── 01_classification.json
│   │   ├── 02_extraction.json
│   │   ├── ...
│   │   └── Postprocessing_Data.json
│   └── .../
│
├── alf_output/                        # ALF writes corrected outputs here
│   ├── case_001/
│   │   ├── Postprocessing_Data.json
│   │   └── alf_audit_log.json
│   └── .../
│
├── investigation_output/              # Investigation reports
├── eval_results/                      # Evaluation results
├── learning_sessions/                 # SME session logs
│
└── config/                            # User-facing configuration files
    ├── rule_base.json                 # SMEs review and approve rules here
    ├── reconstructed_rules_book.md    # Validation rules (editable by admins)
    └── rule_discovery_cache.json      # Cached rule discovery
```

### Required Environment Variables

Add the following to `.env` for production GCS integration:

```bash
# GCS Integration (production mode)
GCS_ENABLED=true
GCS_BUCKET=your-invoice-processing-bucket
GCS_INPUT_PREFIX=incoming_cases       # where incoming invoice cases are uploaded
GCS_OUTPUT_PREFIX=agent_output        # where agent writes intermediate artifacts
GCS_ALF_PREFIX=alf_output             # where ALF writes corrected outputs
GCS_CONFIG_PREFIX=config              # where rule_base.json and rules_book.md live
```

### Code Changes Required for Production

The following files need modification to support GCS I/O instead of local file paths:

| File | What to Change |
|------|----------------|
| `invoice_processing/core/config.py` | Add GCS path resolution: when `GCS_ENABLED=true`, resolve `DATA_DIR`, `AGENTIC_FLOW_OUT`, `ALF_OUT_DIR`, `RULE_BASE_PATH`, `RULES_BOOK_PATH`, and `SESSIONS_DIR` to GCS paths instead of local paths |
| `invoice_processing/agent.py` | Update `run_inference()` to read source cases from GCS (`gs://{BUCKET}/incoming_cases/{case_id}/`) and write outputs to GCS |
| `invoice_processing/shared_libraries/acting/general_invoice_agent.py` | Replace local `OUTPUT_BASE_DIR` file I/O with GCS reads/writes using `google-cloud-storage` client |
| `invoice_processing/shared_libraries/investigation/investigate_agent_reconst.py` | Update `AGENT_OUTPUT_DIR`, `INVESTIGATION_OUTPUT_DIR`, and `RULES_BOOK_PATH` to read from/write to GCS |
| `invoice_processing/shared_libraries/alf_engine.py` | Update `ALF_OUT_DIR` and rule base loading to use GCS |
| `invoice_processing/core/rule_writer.py` | Update `RULE_BASE_PATH` reads/writes and backup logic for GCS |
| `invoice_processing/tools/tools.py` | Update `EXEMPLARY_DIR` and `DATA_DIR` to support GCS paths |

### User-Facing Files

In production, the following files should be accessible to SMEs and administrators through the GCS bucket (or a UI built on top of it):

| File | Audience | Access | Purpose |
|------|----------|--------|---------|
| `config/rule_base.json` | SMEs, Admins | Read/Write | Review, approve, and manually edit ALF correction rules |
| `config/reconstructed_rules_book.md` | Admins | Read/Write | Update the validation rules constitution that the investigation layer validates against |
| `alf_output/{case_id}/Postprocessing_Data.json` | AP Team | Read | Review ALF-corrected invoice decisions |
| `agent_output/{case_id}/Postprocessing_Data.json` | AP Team | Read | Review original agent decisions before ALF correction |
| `learning_sessions/*.json` | Admins | Read | Audit trail of SME rule creation sessions |

---

## Sample Test Cases

The agent ships with 3 sample invoice cases in `exemplary_data/`:

| Case | Vendor | Total | Acting Decision | Phase | Scenario |
|------|--------|-------|-----------------|-------|----------|
| case_001 | FastTrack Logistics | $733.70 | REJECT | Phase 3 | Vendor tax ID invalid |
| case_002 | Precision Tech Co Pty Ltd | $555.50 | ACCEPT | -- | Preventative maintenance, 3 line items, all valid |
| case_005 | QuickFix HVAC Repairs | $1,069.32 | REJECT | Phase 4 | Labour hours not authorized -- no WAF submitted (Step 4.3) |
