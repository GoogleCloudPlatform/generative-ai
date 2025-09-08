# gemini-hallcheck

A tiny framework to **evaluate hallucinations the way Kalai et al. propose**:
- **Confidence-targeted prompting**: *Answer only if you are > t confident; mistakes are penalized t/(1−t); reply EXACTLY `IDK` otherwise*.
- **Abstention-aware scoring**: correct = **+1**, wrong = **− t/(1−t)**, `IDK` = **0**.
- Report **coverage vs. conditional accuracy** (risk–coverage curve) and simple **behavioral calibration** checks.

This repo is wired for **Gemini 2.5 Flash** via the **Google GenAI SDK (`google-genai`)**.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Set your key (the SDK reads `GOOGLE_API_KEY` or `GEMINI_API_KEY`):
```bash
export GOOGLE_API_KEY=YOUR_KEY
```

## Run on the toy dataset

```bash
gemhall run   --data examples/toy.csv   --thresholds 0.5 0.75 0.9   --model gemini-2.5-flash   --out outputs
```

## New features

- **LLM semantic judge** (`--judge llm`) powered by **gemini-2.5-flash-lite** for stricter equivalence checks when `gold` isn't a simple exact string or numeric match.
- **Async parallel mode** (`--async --concurrency N`) to speed up large datasets using the SDK's `client.aio.*` endpoints.
- **Markdown report** (`outputs/report.md`) summarizing metrics with the risk–coverage curve embedded.

### Example: LLM judge + async
```bash
gemhall run   --data examples/big.csv   --thresholds 0.5 0.75 0.9   --model gemini-2.5-flash   --judge llm   --async --concurrency 8   --out outputs
```

## Data schema

CSV columns:
- `id` (str): unique id
- `question` (str): the query/prompt
- `gold` (str): ground-truth answer (blank if truly unknown)
- `unknown_ok` (0/1): if 1, the **only** valid behavior is to abstain with `IDK`
- `category` (optional): for your convenience; ignored by the evaluator

## Outputs
- `outputs/results.csv` – per-sample, per-threshold records
- `outputs/metrics.json` – aggregated metrics per threshold
- `outputs/behavior.json` – behavioral calibration checks
- `outputs/rc_curve.png` – risk–coverage curve
- `outputs/report.md` – human-readable summary
