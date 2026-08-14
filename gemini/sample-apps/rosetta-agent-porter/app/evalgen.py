# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
"""Stage 5 — fidelity eval: prove the ported ADK agent is faithful to the source.

The porting pipeline (stages 1-4) produces a ported ADK project. This stage
*validates* the port behaviorally: it runs the PORTED root_agent on real inputs
mined from the source repo (via `acli.run_capture`, in the port's own venv), then
LLM-judges each response against a rubric derived from the ORIGINAL agent's
intended behavior. The output is a `FidelityReport` (mean case score + per-case
verdicts + verified tricky-mapping notes).

Judge/synth path: this is a raw structured-output grading call (deterministic,
schema-locked), so we use `google.genai` directly with a Pydantic
`response_schema`, so grading is deterministic JSON rather than free text
— rather than the ADK `make_model` wrapper. The backend env is already set by importing
`app.config` (which loads .env with override=True). Grading runs on the SMART
model (config.MODEL_SMART), matching the `eval_author` role in config.ROLE_MODEL.
"""

from __future__ import annotations

import asyncio
import statistics
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app import acli, config
from app.schemas import EvalCase, FidelityReport

# Default dataset size. Each case runs the FULL ported agent end-to-end (slow
# agents take minutes), so we keep this small; callers can override via
# `max_cases`. Never larger than the pipeline-wide cap.
_DEFAULT_MAX_CASES = 3


# --------------------------------------------------------------------------- #
# structured-output verdict (the judge) + synthesized-case schema
# --------------------------------------------------------------------------- #
class _Verdict(BaseModel):
    """LLM-as-judge output — schema-locked so grading is deterministic JSON."""

    verdict: Literal["pass", "partial", "fail"] = Field(
        description="pass = clearly fulfills the original agent's intended behavior; "
        "partial = partially fulfills; fail = wrong, empty, or crashed."
    )
    score: float = Field(description="0..1 faithfulness score for this single case.")
    rationale: str = Field(description="One or two sentences justifying the verdict.")


class _Cases(BaseModel):
    cases: list[str] = Field(
        default_factory=list,
        description="Representative user inputs a real user would send this agent.",
    )


_CLIENT: genai.Client | None = None


def _client() -> genai.Client:
    """genai client for the configured backend (env pinned by importing app.config).

    Cached at module level, and that is load-bearing: callers use it as
    `_client().models.generate_content(...)`, so a freshly built client would be
    a temporary with no strong reference. CPython can finalize it while the
    request is still being set up, and the finalizer closes the underlying
    transport — every call then fails with "Cannot send a request, as the client
    has been closed" and each eval case scores 0 with a "Judge error". Holding
    one reference here fixes it (httpx clients are thread-safe, and the judge
    runs under asyncio.to_thread).
    """
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = genai.Client()
    return _CLIENT


# --------------------------------------------------------------------------- #
# rubric: what the ORIGINAL agent is supposed to do
# --------------------------------------------------------------------------- #
def _expected_behavior(agent_summary: str, analyses: dict) -> str:
    """Short natural-language description of the ORIGINAL agent's intended behavior.

    Derived deterministically from the mined agent_summary plus the analysis
    swarm's graph/tools/models facets (no model call — cheap + stable). This is
    the rubric the judge grades faithfulness against, e.g. "scopes the query,
    runs web research via search, returns a structured cited report".
    """
    analyses = analyses or {}
    bits: list[str] = []
    summary = (agent_summary or "").strip()
    if summary:
        bits.append(summary if summary.endswith(".") else summary + ".")

    graph = analyses.get("analysis_graph") or {}
    cf = graph.get("control_flow")
    loops = graph.get("loops") or []
    fan_out = graph.get("fan_out") or []
    if cf:
        shape = {
            "linear": "follows a fixed multi-step pipeline",
            "branching": "routes/branches based on the query",
            "cyclic": "iterates in a reason/act loop until done",
            "hierarchical": "delegates to specialised sub-agents",
        }.get(cf, f"has a {cf} control flow")
        clause = f"Internally it {shape}"
        if loops:
            clause += " (reflection/ReAct loops)"
        if fan_out:
            clause += " and fans out parallel work"
        bits.append(clause + ".")

    tools = (analyses.get("analysis_tools") or {}).get("tools") or []
    tool_names = ", ".join(
        f"{t.get('name')} ({t.get('kind')})" for t in tools if t.get("name")
    )
    if tool_names:
        bits.append(f"It uses tools: {tool_names}.")

    models = analyses.get("analysis_models") or {}
    if models.get("search_api"):
        bits.append(f"Web search is backed by {models['search_api']}.")

    if not bits:
        bits.append("Answer the user's request helpfully, correctly, and completely.")
    return " ".join(bits)


# --------------------------------------------------------------------------- #
# the judge — grade one ported response against the rubric
# --------------------------------------------------------------------------- #
def _judge(
    case: str, response: str, agent_summary: str, expected_behavior: str
) -> EvalCase:
    """LLM-judge a single ported response for behavioral faithfulness.

    Grades whether the ported agent's output fulfills the ORIGINAL agent's
    intended behavior for this input — faithfulness of behavior + output quality,
    NOT exact wording. Robust: empty/crashed responses and judge errors resolve
    to a 'fail' EvalCase rather than raising.
    """
    if not (response or "").strip():
        return EvalCase(
            input=case,
            verdict="fail",
            score=0.0,
            rationale="Ported agent returned empty output (crash/timeout/no answer).",
        )

    prompt = (
        "You are grading whether a PORTED agent faithfully reproduces the behavior "
        "of the ORIGINAL agent it was ported from. Judge faithfulness of behavior "
        "and output quality for the given input — NOT exact wording.\n\n"
        "Verdicts: pass = the response clearly fulfills the original agent's "
        "intended behavior; partial = it partially fulfills it (incomplete, "
        "shallow, or missing part of the expected output); fail = it is wrong, "
        "empty, off-task, or crashed.\n\n"
        f"ORIGINAL AGENT SUMMARY:\n{agent_summary}\n\n"
        f"ORIGINAL AGENT'S INTENDED BEHAVIOR (rubric):\n{expected_behavior}\n\n"
        f"USER INPUT:\n{case}\n\n"
        f"PORTED AGENT'S RESPONSE:\n{response}\n\n"
        "Return a verdict, a 0..1 score, and a one-sentence rationale."
    )
    try:
        resp = _client().models.generate_content(
            model=config.MODEL_SMART,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,  # deterministic grading
                response_mime_type="application/json",
                response_schema=_Verdict,
            ),
        )
        v = resp.parsed
        if v is None:
            return EvalCase(
                input=case,
                verdict="fail",
                score=0.0,
                rationale="Judge returned no parseable verdict.",
            )
        return EvalCase(
            input=case,
            verdict=v.verdict,
            score=max(0.0, min(1.0, float(v.score))),
            rationale=v.rationale,
        )
    except (
        Exception
    ) as e:  # broad except on purpose: a judge error must not sink the run
        return EvalCase(
            input=case,
            verdict="fail",
            score=0.0,
            rationale=f"Judge error: {e}",
        )


# --------------------------------------------------------------------------- #
# fallback: synthesize inputs when the repo had none
# --------------------------------------------------------------------------- #
def _synthesize_cases(agent_summary: str, n: int) -> list[str]:
    """Generate `n` representative user inputs from the agent summary.

    Used only when the source repo yielded no mined example inputs. Best-effort:
    on any failure returns a single generic probe so eval can still proceed.
    """
    n = max(1, n)
    prompt = (
        f"An AI agent is described as: {agent_summary}\n\n"
        f"Produce {n} varied, realistic user inputs a real user would send this "
        "agent to exercise its core behavior. Each should be a complete standalone "
        "request. Return only the list of input strings."
    )
    try:
        resp = _client().models.generate_content(
            model=config.MODEL_SMART,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                response_mime_type="application/json",
                response_schema=_Cases,
            ),
        )
        v = resp.parsed
        if v and v.cases:
            cases = [c.strip() for c in v.cases if c and c.strip()]
            if cases:
                return cases[:n]
    except Exception:  # broad except on purpose: fall through to a generic probe
        pass
    return ["What can you do, and can you show me with a concrete example?"][:n] or [
        "What can you do?"
    ]


# --------------------------------------------------------------------------- #
# report notes: verified tricky-mapping annotations (if inferable)
# --------------------------------------------------------------------------- #
def _fidelity_notes(
    analyses: dict, cases: list[EvalCase], synthesized: bool
) -> list[str]:
    analyses = analyses or {}
    notes: list[str] = []
    if synthesized:
        notes.append("inputs synthesized (repo had no mined example inputs)")
    graph = analyses.get("analysis_graph") or {}
    passed = sum(1 for c in cases if c.verdict == "pass")
    total = len(cases) or 1
    fan_out = graph.get("fan_out") or []
    loops = graph.get("loops") or []
    if fan_out and passed:
        notes.append(
            f"dynamic fan-out exercised ({', '.join(map(str, fan_out))[:80]}); "
            f"{passed}/{total} cases faithful"
        )
    if loops and passed:
        notes.append(
            f"reason/act loop exercised ({', '.join(map(str, loops))[:80]}); "
            f"{passed}/{total} cases faithful"
        )
    return notes


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #
async def evaluate_fidelity(
    project: Path,
    mined_inputs: list[dict],
    agent_summary: str,
    analyses: dict,
    *,
    max_cases: int | None = None,
) -> AsyncGenerator[dict, None]:
    """Run + judge the ported agent for fidelity; stream progress events.

    Yields `{"type": "eval_case", "data": EvalCase}` per case, then a final
    `{"type": "fidelity", "data": FidelityReport}`. Event dicts follow the
    pipeline's `{"type", "data"}` shape.

    Args:
      project: path to the ported ADK project (has its own venv).
      mined_inputs: list of `{"text", "source"}` dicts mined from the source repo
        (EvalInputs.inputs). If empty, inputs are synthesized from agent_summary.
      agent_summary: 1-2 sentence description of what the ORIGINAL agent does.
      analyses: the analysis-swarm facets (graph/tools/models/...) — used to build
        the judge rubric and infer verified tricky-mapping notes.
      max_cases: cap on cases to run (default ~3 to keep it fast).

    Resilient by design: a single case that crashes, times out, or returns empty
    becomes a 'fail' EvalCase — it never raises out of the generator.
    """
    cap = (
        max_cases
        if max_cases is not None
        else min(_DEFAULT_MAX_CASES, config.MAX_EVAL_CASES)
    )
    cap = max(1, cap)

    # pick cases: prefer real mined inputs, else synthesize
    cases: list[str] = []
    for mi in mined_inputs or []:
        text = (mi.get("text") if isinstance(mi, dict) else str(mi)) or ""
        text = text.strip()
        if text:
            cases.append(text)
    cases = cases[:cap]
    synthesized = False
    if not cases:
        synthesized = True
        cases = _synthesize_cases(agent_summary, cap)

    expected_behavior = _expected_behavior(agent_summary, analyses)

    results: list[EvalCase] = []
    for case in cases:
        try:
            ok, resp = await asyncio.to_thread(acli.run_capture, project, case)
        except Exception as e:  # broad except on purpose: capture failure -> fail case
            ok, resp = False, f"run_capture error: {e}"

        if not ok:
            ec = EvalCase(
                input=case,
                verdict="fail",
                score=0.0,
                rationale=(
                    "Ported agent produced no usable output "
                    f"(crash/empty/timeout): {resp[:300]}"
                ).strip(),
            )
        else:
            ec = await asyncio.to_thread(
                _judge, case, resp, agent_summary, expected_behavior
            )
        results.append(ec)
        yield {"type": "eval_case", "data": ec.model_dump()}

    score = round(statistics.fmean([c.score for c in results]), 3) if results else 0.0
    report = FidelityReport(
        score=score,
        cases=results,
        notes=_fidelity_notes(analyses, results, synthesized),
    )
    yield {"type": "fidelity", "data": report.model_dump()}
