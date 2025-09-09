# gemini-hallcheck

Confidence-targeted evaluation with abstention-aware scoring for Gemini via `google-genai`.

- Enforces: *Answer only if you are > t confident; else reply EXACTLY `IDK`.*  
  Scoring: correct = **+1**, wrong = **−t/(1−t)**, IDK = **0**.
- Reports coverage, conditional accuracy (1 − hallucination rate among answers), and a labeled risk–coverage curve.
- Supports **LLM semantic judge** (Gemini 2.5 Flash-Lite), **async**, **progress bar**.
- Direct **MMLU** integration (Hugging Face Datasets) with **`--limit`** sampling and **`--idk-frac`** to mix in abstain-only items.
- **Quota-aware** client: `--rpm-limit` (client-side throttle) and `--max-retries` with backoff honoring server `RetryInfo` on 429s.

## Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
export GOOGLE_API_KEY=YOUR_KEY   # or GEMINI_API_KEY
```

## CSV mode
```bash
gemhall run   --data examples/toy.csv   --thresholds 0.5 0.75 0.9   --model gemini-2.5-flash-lite   --progress   --out outputs
```

## MMLU (direct) with sampling + IDK mixing
```bash
gemhall mmlu   --thresholds 0.5 0.75 0.9   --model gemini-2.5-flash-lite   --split test   --subjects all   --limit 200   --idk-frac 0.3   --judge llm   --async --concurrency 16   --rpm-limit 300   --max-retries 8   --progress   --out outputs/mmlu_mix
```

`--idk-frac` converts the given fraction of sampled items into **IDK-only** questions by corrupting the correct option (no A/B/C/D is right), marking `unknown_ok=1, gold=""`.

## Outputs
- `results.csv`, `metrics.json`, `behavior.json`, `rc_curve.png` (points labeled with `t=`), `report.md`.
