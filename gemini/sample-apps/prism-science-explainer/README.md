# Prism — ask a science question, get an interactive explainer

| Author(s) |
| --------- |
| [Lavi Nigam](https://www.linkedin.com/in/lavinigam/) |

Ask Prism a plain question — *"how do rainbows form?"* — and it researches the answer
across the live web, then **writes you a small interactive instrument** to explain it:
a running simulation with controls you can drag, built on the spot for your question.
No template library, no pre-canned answers. About 45 seconds, start to finish.

Every stage runs on a single model:
**[Gemini 3.7 Flash](https://ai.google.dev/gemini-api/docs/models)**.

![Prism: the question "How do rainbows form?" has produced a live interactive instrument showing a rainbow arc over a rainy landscape, with an observer, an inset diagram of light refracting inside a single droplet, a Sun-elevation slider, and play/step/reset controls.](images/prism-hero.png)

## What it does

![Prism architecture: a science question, "how do rainbows form?", enters the Prism backend (FastAPI plus Google ADK, running one model, Gemini 3.7 Flash), which runs five stages - a gatekeeper that checks the question is teachable science and sets the audience level, a planner that splits it into five research angles, an ADK ParallelAgent research swarm of five agents at once covering mechanism, key numbers, misconception, limits and a worked example, all grounded in Google Search, then build instrument, which writes the PRISM_SPEC and PRISM_SIM simulation, and verify, which checks that it animates and that the controls drive it, with a repair loop back to build - and outputs an interactive explainer running live with its sources.](images/architecture.png)

One model does all of it. What changes per stage is the **thinking level**, not the
model: the gatekeeper, planner and the five parallel searchers run at `LOW` to stay
fast, while the instrument builder thinks at `MEDIUM`. See `THINK` and `MODES` in
[`app/config.py`](app/config.py).

The interesting part is the last three steps. Getting a model to emit a *working*
simulation — one that is still visibly moving at t=30s, where dragging a slider changes
the animation already playing — is mostly a prompt-and-verification problem.
[`app/fill_prompt.txt`](app/fill_prompt.txt) carries a hard motion contract, and
[`app/render.py`](app/render.py) statically rejects an instrument whose `step()` is
empty, which is the classic failure: a beautiful scene where Play does nothing.

## Prerequisites

| Tool | Why | Install |
| --- | --- | --- |
| Python 3.11–3.13 | runtime | <https://www.python.org/downloads/> |
| `uv` | dependency + venv manager | <https://docs.astral.sh/uv/getting-started/installation/> |

Plus access to Gemini through **either** of the two backends below.

## Setup

```bash
git clone https://github.com/GoogleCloudPlatform/generative-ai.git
cd generative-ai/gemini/sample-apps/prism-science-explainer

make setup     # checks the tools above, installs deps, creates .env
```

Then open `.env` and configure **one** backend.

### Option A — Gemini API (Google AI Studio)

The quickest way to start. Get a key at
[aistudio.google.com/apikey](https://aistudio.google.com/apikey):

```bash
GOOGLE_API_KEY=your-api-key-here
```

### Option B — Gemini Enterprise Agent Platform

Use your own Google Cloud project:

```bash
gcloud auth application-default login
gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT_ID
```

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
```

Prism picks the backend automatically: if `GOOGLE_API_KEY` is set it uses the Gemini
API, otherwise it uses Gemini Enterprise Agent Platform. Set
`GOOGLE_GENAI_USE_VERTEXAI=true|false` to force one. Variables exported in your shell
take precedence over `.env`.

> **If you see `503 … currently experiencing high demand`**, the Gemini API tier is
> busy. One Prism run makes ~11 model calls in a burst, so it is more exposed to this
> than a single-shot script. Wait and retry, or use Gemini Enterprise Agent Platform
> (Option B), which has been the more reliable of the two for this workload.

## Run it

```bash
make demo
```

Open <http://127.0.0.1:8040> and ask something. Good first questions:

- `Why is the sky blue?`
- `How do rainbows form?`
- `How does a swing work?`
- `What makes ice float?`

Each run streams its progress live — you watch the five researchers finish, the sources
arrive, and the instrument get written.

### Modes

Every mode runs the same model. What differs is how much it deliberates and how much of
the page it writes:

| Mode | Approach | Typical | Use it for |
| --- | --- | --- | --- |
| `fast` | fills a prepared shell, `LOW` thinking | ~35 s | quick answers |
| `balanced` *(default)* | fills a prepared shell, `MEDIUM` thinking | ~45 s | the tuned instrument |
| `freeform` | writes a whole bespoke HTML page | ~45 s | letting it off the leash |

### Other commands

```bash
make test      # unit tests
make lint      # ruff check + format --check
make help      # everything else
```

## How it works

Prism is an ADK multi-agent system. The research swarm is a real ADK `ParallelAgent`;
the self-heal loop feeds verification errors back into generation.

| Path | What lives there |
| --- | --- |
| [`app/agent.py`](app/agent.py) | the orchestrator — the whole pipeline, streamed as events |
| [`app/agents.py`](app/agents.py) | the agent roster: gatekeeper, planner, the 5-way swarm, builders |
| [`app/prompts.py`](app/prompts.py) | every prompt, including the generative-UI contract |
| [`app/fill_prompt.txt`](app/fill_prompt.txt) | the motion + composition contract for the instrument |
| [`app/shell.html`](app/shell.html) | the fixed instrument shell: canvas, controls, animation loop |
| [`app/render.py`](app/render.py) | splices the generated payload into the shell, rejects inert output |
| [`app/config.py`](app/config.py) | the model, per-role thinking levels, backend selection |
| [`serve.py`](serve.py) | FastAPI server; streams the run to the browser as SSE |
| [`frontend/index.html`](frontend/index.html) | the single-page UI |

Two details worth knowing if you read the code:

- **Grounding is real.** The five research workers use ADK's built-in `google_search`
  tool, and every citation shown in the UI is mined from the model's own
  `grounding_metadata` — nothing is invented. A typical run cites 30–45 sources.
- **The instrument is verified, not trusted.** `check_fill` parses the generated
  payload and fails it if `step()` is missing or empty, or if the controls are never
  read inside the animation loop. A failure triggers a repair pass.

## Deploy to Cloud Run (optional)

```bash
make deploy GCP_PROJECT=your-project-id
```

Builds the container, creates a runtime service account with `roles/aiplatform.user`,
and deploys to Cloud Run using Gemini Enterprise Agent Platform — no API key in the
container. The service is deployed **private** (`--no-allow-unauthenticated`); the
script prints the command to
grant yourself access. Put real authentication in front of it before exposing it to
anyone else.

## Costs

Each run makes roughly eleven model calls — a gatekeeper, a planner, five parallel
grounded searches, the instrument build and any repair — so it is not free.
**Google Search grounding is a billable feature** and is charged separately from
tokens. On the Gemini API free tier you may hit rate limits, or `503` responses, if you
run several questions back to back.

See [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) and
[Gemini Enterprise Agent Platform pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing).

## Limitations

- The instruments are generated by a model. They are grounded in live search results and
  checked to animate and respond, but **nothing verifies the physics is right** — treat
  an instrument as a well-read first draft, not a textbook.
- Prism is scoped to science/STEM questions. The gatekeeper declines everything else.
- Quality varies by topic. Concepts with a familiar visual (sky, rainbows, swings, waves)
  produce the strongest instruments; highly abstract topics are hit and miss.
- The self-heal loop is capped at one repair pass by default.

## Disclaimer

This is not an officially supported Google product. It is sample code, provided as-is,
to demonstrate what Gemini 3.7 Flash and ADK can do together.
