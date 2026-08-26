# fx-agent: run the agent quality flywheel with agents-cli

Author: [Lavi Nigam](https://github.com/lavinigam-gcp)

Companion code for the blog post "Run the Agent Quality Flywheel Yourself: A Hands-On Guide with agents-cli."

`fx-agent` is a tiny currency-conversion agent with one tool. It exists to demonstrate one loop end to end: catch a real failure with an evaluation, fix it with a one-line change, and prove the fix moved the metric you care about. Everything here was run against the Gemini Enterprise Agent Platform evaluation service on `gemini-3.7-flash`.

The seeded bug: the baseline instruction never asks the agent to end its answer with a `Tools used:` footer, so the model never writes one. A custom metric makes that behavior countable, and a one-line instruction change takes it from 0 of 6 to 6 of 6.

## Prerequisites

- A Google Cloud project with Vertex AI and the Agent Platform evaluation service enabled.
- Access to `gemini-3.7-flash` on Vertex AI in your project and region.
- Application default credentials: `gcloud auth application-default login`.
- [`uv`](https://docs.astral.sh/uv/) and [`agents-cli`](https://adk.dev/get-started/agents-cli/): `uv tool install google-agents-cli`.

## Setup

```bash
uv venv && uv pip install "google-adk[eval]" "google-cloud-aiplatform[evaluation]"
cp .env.example .env       # then set GOOGLE_CLOUD_PROJECT to your project id
```

`.env` should contain:

```bash
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
```

## Run the loop

The dataset is `tests/eval/datasets/fx-dataset.json` (six single-turn conversions). The custom metrics live in `fx_footer_config.yaml`: `tools_footer_present` (an LLM-as-judge rubric) and `tools_footer_present_code` (a deterministic regex check, no model call).

### 1. Baseline (reproduces 0 of 6)

In `app/agent.py`, set `INSTRUCTION = BASELINE_INSTRUCTION`, then:

```bash
# built-in autorater metrics
agents-cli eval run --dataset tests/eval/datasets/fx-dataset.json \
  --metrics tool_use_quality,instruction_following,final_response_quality \
  --output artifacts/baseline_ootb/

# custom footer metrics (generate traces, then grade)
agents-cli eval generate --dataset tests/eval/datasets/fx-dataset.json \
  --output artifacts/baseline_traces.json
agents-cli eval grade --traces artifacts/baseline_traces.json \
  --config fx_footer_config.yaml --output artifacts/baseline_footer/
```

### 2. Fix and re-run (reproduces 6 of 6)

In `app/agent.py`, set `INSTRUCTION = FIXED_INSTRUCTION`, then re-run the same three commands into `candidate_ootb/`, `candidate_traces.json`, and `candidate_footer/`, and compare:

`eval grade` writes a `results_<ts>.json` file (with a run timestamp) into each output directory and prints its path. Pass the two result files to `eval compare` (the command below picks the newest in each folder):

```bash
agents-cli eval compare \
  "$(ls -t artifacts/baseline_footer/results_*.json | head -1)" \
  "$(ls -t artifacts/candidate_footer/results_*.json | head -1)"
```

## Expected results (gemini-3.7-flash, 6 cases)

| Metric | Baseline | After fix |
| --- | --- | --- |
| `tools_footer_present` (LLM judge) | 0 of 6 | 6 of 6 |
| `tools_footer_present_code` (deterministic) | 0 of 6 | 6 of 6 |
| `instruction_following` | 0.83 pass | 1.00 pass |
| `tool_use_quality` | 1.00 | 1.00 |
| `final_response_quality` | 0.83 pass | 1.00 pass |

Scores from model-based graders can shift slightly between runs. Trust the delta between runs more than any single absolute number. The deterministic `tools_footer_present_code` check is stable because it never calls a model.

## What is in here

```text
app/agent.py                          the agent, tool, and both instructions (baseline + fixed)
tests/eval/datasets/fx-dataset.json   the 6-case eval set
fx_footer_config.yaml                 the two custom metrics
pyproject.toml                        project + eval dependencies
.env.example                          copy to .env and set your project
```

## Notes and troubleshooting

- Custom metric config: do not set `judge_model` in `fx_footer_config.yaml`. Passing an explicit model is rejected by the eval service with "Invalid autorater model resource name"; omit it to use the service default autorater.
- `agents-cli` prints a harmless skills version-mismatch warning on each `eval` invocation. It is cosmetic.
- On a fresh clone, the first `agents-cli eval` command may fail with "Local server did not start within 30s". This is the one-time `uv run` project build exceeding the boot timeout, not a real error. Re-run the command (the environment is warm now), or pre-warm once with `uv run python -c "import app.agent"` before the first eval.

- On some managed or corporate machines that use context-aware access certificates, google-auth can fail with a mutual-TLS error ("Cert provider command returns non-zero status code"). If you hit this, set `GOOGLE_API_USE_CLIENT_CERTIFICATE=false`. Most developers using standard application default credentials never need this.

## License

Apache License 2.0. See the `LICENSE` file at the repository root.
