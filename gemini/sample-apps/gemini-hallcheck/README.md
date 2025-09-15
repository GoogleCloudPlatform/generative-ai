# gemini-hallcheck

Confidence-targeted, abstention-aware hallucination evaluator for Gemini via `google-genai`.

- Implements the Kalai et al. idea in practice: **"Answer only if you're > t confident; otherwise say `IDK`."**
- Scores with an abstention-aware loss: **correct = +1, wrong = −t/(1−t), IDK = 0**.
- Produces a **risk–coverage curve** (conditional accuracy vs. coverage) with **labeled t-points**.
- Works from **CSV** or directly from **MMLU** (Hugging Face), with **random sampling** and an **`--idk-frac`** mixer to create **IDK-only** items (tests true abstention).
- **LLM semantic judge** (Gemini 2.5 Flash-Lite) or **exact** judge.
- **Async** with progress bar, **quota-aware retries** (honors server `RetryInfo`) and optional **client-side RPM throttle**.
- Runs on **Gemini API** or **Vertex AI** (env-based switch).

> ℹ️ We do **not** implement MMLU-Pro here.

---

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

### Auth options

**Gemini API (Developer API):**

```bash
export GOOGLE_API_KEY=YOUR_KEY  # or GEMINI_API_KEY
```

**Vertex AI:**

```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT=your-gcp-project
export GOOGLE_CLOUD_LOCATION=us-central1   # or europe-west1, etc.
# Do NOT set GOOGLE_API_KEY when using Vertex AI mode.
```

---

## Quickstart

### CSV mode

```bash
gemhall run   --data examples/toy.csv   --thresholds 0.5 0.75 0.9   --model gemini-2.5-flash-lite   --progress   --out outputs
```

### MMLU (direct from HF Datasets)

```bash
gemhall mmlu   --thresholds 0.5 0.75 0.9   --model gemini-2.5-flash-lite   --split test   --subjects all   --limit 200   --judge llm   --async --concurrency 16   --progress   --out outputs/mmlu
```

**Mix in "IDK-only" items** (turns a fraction of sampled items into unanswerables so the only correct behavior is `IDK`):

```bash
  --idk-frac 0.3
```

---

## What you get

- `results.csv` – one row per (item × t): prediction, abstained flag, correctness, score
- `metrics.json` – coverage, conditional accuracy (on answers), hallucination rate among answers, avg expected score
- `behavior.json` – simple behavior checks (e.g., monotonic coverage as t increases)
- `rc_curve.png` – **risk–coverage curve** with **"t=…"** labels on each point
- `report.md` – short summary plus the chart embedded

---

## Interpreting the curve

- **Coverage** (x-axis): fraction of items the model answered (didn't say `IDK`).
- **Conditional accuracy** (y-axis): how often it was correct **when it did answer**.
- As **t** rises ⇒ coverage falls, conditional accuracy should rise.
- If **accuracy at t** is **well below t**, the model is **over-confident or non-compliant** → raise t, harden prompts, add retrieval/handoffs, or re-calibrate.

---

## CLI reference

Shared flags (both `run` and `mmlu`):

```sh
--thresholds FLOAT...      Confidence thresholds (e.g., 0.5 0.75 0.9)  [required]
--model TEXT               Gemini model id (default: gemini-2.5-flash)
--temperature FLOAT        Sampling temperature (default: 0.0)
--thinking-budget INT      Optional thinking budget (default: 0)
--seed INT                 RNG seed for sampling (default: 1234)
--judge {exact,llm}        Validity judge (exact or LLM; default: exact)
--async                    Use async client for parallel requests
--concurrency INT          Max concurrent requests in async mode (default: 8)
--progress                 Show a progress bar
--out PATH                 Output directory (default: outputs)
--rpm-limit INT            Client-side requests-per-minute cap (optional)
--max-retries INT          Max retries on 429 with backoff (default: 6)
```

`run` (CSV):

```sh
--data PATH                CSV with columns: id, question, gold, unknown_ok
```

`mmlu` (Hugging Face "cais/mmlu"):

```sh
--split TEXT               Split (e.g., test, dev)  [default: test]
--subjects STR...          Subject names or 'all'   [default: all]
--limit INT                Randomly sample N items after filtering subjects
--idk-frac FLOAT           Fraction [0..1] to convert to IDK-only items (default: 0.0)
```

**MMLU loader notes:**
We first try the unified `"all"` config and fall back to stitching per-subject configs if needed. No `trust_remote_code` required. We also ensure a `subject` column exists.

---

## Judges

- **exact** – strict match for MCQ (letters A/B/C/D), or numerical/text equality for free-form.
- **llm** – Gemini 2.5 Flash-Lite "YES/NO" grader; for `unknown_ok=1`, only `IDK` is considered correct (no LLM call).

---

## IDK detection & scoring

- We normalize model outputs; `IDK` is recognized case-insensitively with common variants.
- Score per item at threshold **t**:
  - answered & correct: **+1**
  - answered & wrong: **−t/(1−t)**
  - abstained (`IDK`): **0**

---

## Rate limits & retries

- If you omit `--rpm-limit`, we still **auto-retry** on `429 RESOURCE_EXHAUSTED`, honoring server **`RetryInfo`** with jittered exponential backoff.
- Set `--rpm-limit` to smooth out bursts and avoid 429s when running with high `--concurrency`.
- Typical stable settings: `--async --concurrency 12 --rpm-limit 180 --max-retries 8`.

---

## Business mapping

- **t≈0.5: Drafting & triage** – high coverage, human-in-the-loop
- **t≈0.75: Assistive answers** – support suggestions, FAQ with citations
- **t≈0.9: Self-serve replies** – public answers in non-regulated flows
- **t≈0.95: High-stakes** – regulated/brand-critical, else handoff

---

## Troubleshooting

- **MMLU config error**: we now request `"all"` and fall back per-subject; ensure `datasets>=2.18.0`.
- **Curly-brace crash in prompts**: fixed by using f-strings (brace-safe).
- **429 quota**: use `--rpm-limit`, and/or lower `--concurrency`.
- **Vertex AI vs API key**: set `GOOGLE_GENAI_USE_VERTEXAI=true` (+ project/location) to use Vertex AI; don't set an API key at the same time.

---

## Citation

This project is based on the following paper.

[arXiv:2509.04664](https://arxiv.org/abs/2509.04664)
