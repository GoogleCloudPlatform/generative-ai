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
# See the License for the specific language governing permissions and
# limitations under the License.
"""Prism root orchestrator.

A custom BaseAgent that drives the pipeline: gatekeeper -> planner -> parallel
parallel research swarm -> spec synth -> UI generator -> static verify + one
self-heal pass. Emits compact progress events (prefixed with a sentinel) that the
SSE layer will translate for the frontend; the final event carries the HTML.
"""

import json
import time
from collections.abc import AsyncGenerator
from typing import ClassVar

from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.apps import App
from google.adk.events import Event
from google.genai import types

from app import config
from app.agents import (
    build_gatekeeper,
    build_planner,
    build_swarm,
    build_ui_filler,
    build_ui_fixer,
    build_ui_generator,
)
from app.events import PRISM_EVENT
from app.render import assemble, check_fill
from app.schemas import ResearchPlan
from app.verify import normalize_html, static_check


def _user_text(ctx: InvocationContext) -> str:
    c = getattr(ctx, "user_content", None)
    if c and getattr(c, "parts", None):
        for p in c.parts:
            if getattr(p, "text", None):
                return p.text.strip()
    return ""


def _struct(ctx: InvocationContext, key: str):
    v = ctx.session.state.get(key)
    if v is None:
        return None
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return None
    return v


class PrismOrchestrator(BaseAgent):
    gatekeeper: LlmAgent
    planner: LlmAgent
    gate_plan: ParallelAgent  # gatekeeper + planner run concurrently
    swarm: ParallelAgent
    ui_generator: LlmAgent
    ui_filler_fast: LlmAgent
    ui_filler_balanced: LlmAgent
    ui_fixer: LlmAgent

    model_config: ClassVar[dict] = {"arbitrary_types_allowed": True}

    def _progress(self, ctx: InvocationContext, kind: str, data: dict) -> Event:
        """A UI-facing progress event (parsed out of the stream by the SSE layer).

        invocation_id is required by the managed VertexAiSessionService (Agent
        Runtime) when appending events; InMemorySessionService (local) ignores it.
        """
        payload = PRISM_EVENT + json.dumps({"type": kind, "data": data})
        return Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(role="model", parts=[types.Part(text=payload)]),
        )

    def _final(self, ctx: InvocationContext, text: str) -> Event:
        return Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(role="model", parts=[types.Part(text=text)]),
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        t0 = time.time()
        timings: dict[str, float] = {}

        concept = _user_text(ctx)
        ctx.session.state["concept"] = concept
        ctx.session.state["sources"] = []

        # 1+2) Gatekeeper + planner CONCURRENTLY (overlap to cut pre-UI latency).
        # The planner works from the raw concept while the gatekeeper validates;
        # if the gatekeeper rejects, we simply discard the (wasted) plan.
        yield self._progress(ctx, "phase", {"phase": "gatekeeping"})
        yield self._progress(ctx, "phase", {"phase": "planning"})
        ts = time.time()
        async for ev in self.gate_plan.run_async(ctx):
            yield ev
        dt = round(time.time() - ts, 2)
        # Each ran concurrently but timed itself (callbacks); report real per-step
        # costs, falling back to the combined wall-time if a stamp is missing.
        timings["gatekeeper"] = ctx.session.state.get("dur_gatekeeper", dt)
        timings["planner"] = ctx.session.state.get("dur_planner", dt)
        timings["gate_plan_wall"] = dt

        scope = _struct(ctx, "scope") or {}
        decision = scope.get("decision", "ok")
        if decision in ("unsafe", "reject"):
            if decision == "unsafe":
                msg = (
                    "I can't build an explainer for that request. Try a science, math, "
                    "or engineering concept — e.g. 'how does a neural network learn?'."
                )
            else:
                msg = (
                    "Prism explains science & STEM concepts with interactive "
                    "visualizations. That's outside its scope — try 'Fourier series', "
                    "'orbital mechanics', or 'how does CRISPR work?'."
                )
            yield self._progress(
                ctx,
                "declined",
                {"kind": decision, "message": msg, "reason": scope.get("reason", "")},
            )
            return
        # Adopt the gatekeeper's normalized concept for the swarm + UI (it's ready
        # now). The plan was built from the raw concept, but its subtopic queries
        # stand on their own, so downstream quality is preserved at no latency cost.
        concept = scope.get("concept") or concept
        ctx.session.state["concept"] = concept
        # Thread the audience level through to the template-fill / UI prompts so
        # they can adapt vocabulary and depth (everyday / intermediate / advanced).
        ctx.session.state["level"] = scope.get("level") or "intermediate"

        plan_d = _struct(ctx, "plan")
        if not plan_d or not plan_d.get("subtopics"):
            plan = ResearchPlan(
                concept=concept,
                key_interaction="Explore the core parameter of the concept.",
                viz_hint="canvas-sim",
                subtopics=[{"angle": "overview", "query": concept}],
            )
        else:
            plan = ResearchPlan(**plan_d)
        yield self._progress(ctx, "plan", plan.model_dump())

        # 3) Research swarm (parallel, grounded) --------------------------------
        subs = plan.subtopics[: config.MAX_WORKERS]
        for i in range(config.MAX_WORKERS):
            ctx.session.state[f"brief_{i}"] = (
                f"{subs[i].angle}: {subs[i].query}" if i < len(subs) else "SKIP"
            )
        yield self._progress(
            ctx, "phase", {"phase": "researching", "workers": len(subs)}
        )
        ts = time.time()
        async for ev in self.swarm.run_async(ctx):
            yield ev
        timings["swarm"] = round(time.time() - ts, 2)

        findings = []
        for i in range(len(subs)):
            f = (ctx.session.state.get(f"finding_{i}") or "").strip()
            if f and f.upper() != "SKIP":
                findings.append({"angle": subs[i].angle, "text": f})
                yield self._progress(
                    ctx, "finding", {"angle": subs[i].angle, "text": f}
                )
        sources = ctx.session.state.get("sources") or []
        yield self._progress(ctx, "citation", {"sources": sources})

        # 4) Assemble the brief for the UI generator ---------------------------
        # The model synthesizes the grounded findings AND builds the instrument in
        # one streamed call (folding the old separate 'spec' step in for latency).
        ctx.session.state["findings_block"] = "\n\n".join(
            f"[{x['angle']}]\n{x['text']}" for x in findings
        ) or (
            "(No research findings were retrieved. Explain only the robust, "
            "well-established qualitative intuition for this concept. Do NOT "
            "invent specific numbers, dates, named studies, or citations; keep "
            "claims general and hedge where a precise value would be required.)"
        )
        ctx.session.state["sources_block"] = (
            "\n".join(f"- {s.get('title', '')} :: {s.get('uri', '')}" for s in sources)
            or "(no sources)"
        )
        ctx.session.state["plan_block"] = (
            f"key_interaction: {plan.key_interaction}\nviz_hint: {plan.viz_hint}"
        )

        # 5) UI generation (mode-dependent) ------------------------------------
        mode = ctx.session.state.get("mode") or config.DEFAULT_MODE
        if mode not in config.MODES:
            mode = config.DEFAULT_MODE
        mcfg = config.MODES[mode]
        repairs = 0
        yield self._progress(ctx, "phase", {"phase": "generating", "mode": mode})
        ts = time.time()

        if mcfg["approach"] == "template":
            # Model writes only the small JS payload; shell.html provides the chrome.
            filler = (
                self.ui_filler_balanced if mode == "balanced" else self.ui_filler_fast
            )
            async for ev in filler.run_async(ctx):
                yield ev
            fill = ctx.session.state.get("fill") or ""
            verdict = check_fill(fill)
            while not verdict.ok and repairs < config.MAX_REPAIRS:
                async for ev in filler.run_async(ctx):  # regenerate the payload
                    yield ev
                fill = ctx.session.state.get("fill") or ""
                verdict = check_fill(fill)
                repairs += 1
            html = assemble(fill)
        else:
            # Freeform: full bespoke HTML + static verify + self-heal.
            async for ev in self.ui_generator.run_async(ctx):
                yield ev
            html = normalize_html(ctx.session.state.get("html") or "")
            verdict = static_check(html)
            while not verdict.ok and repairs < config.MAX_REPAIRS:
                ctx.session.state["broken_html"] = html
                ctx.session.state["verdict_errors"] = "; ".join(verdict.errors)
                async for ev in self.ui_fixer.run_async(ctx):
                    yield ev
                html = normalize_html(ctx.session.state.get("html") or "")
                verdict = static_check(html)
                repairs += 1
        timings["ui_gen"] = round(time.time() - ts, 2)

        yield self._progress(ctx, "phase", {"phase": "verifying"})
        ctx.session.state["html"] = html
        yield self._progress(ctx, "verdict", verdict.model_dump())

        metrics = {
            "e2e_s": round(time.time() - t0, 2),
            "timings_s": timings,
            "mode": mode,
            "workers": len(subs),
            "sources": len(sources),
            "repairs": repairs,
            "html_chars": len(html),
        }
        yield self._progress(ctx, "metrics", metrics)

        # Final response: the generated HTML document.
        yield self._final(ctx, html)


def build_root_agent() -> PrismOrchestrator:
    gk = build_gatekeeper()
    pl = build_planner()
    # Gatekeeper (validate) + planner (decompose) overlap: both read only {concept}
    # and write disjoint keys (scope / plan), so they're safe to run concurrently.
    gp = ParallelAgent(name="gate_plan", sub_agents=[gk, pl])
    sw = build_swarm()
    ui = build_ui_generator()  # freeform (full bespoke HTML)
    ff = build_ui_filler(
        "ui_filler_fast",
        config.MODES["fast"]["model"],
        config.MODES["fast"]["thinking"],
    )  # template, minimal thinking
    fb = build_ui_filler(
        "ui_filler_balanced",
        config.MODES["balanced"]["model"],
        config.MODES["balanced"]["thinking"],
    )  # template, low thinking
    fx = build_ui_fixer()
    return PrismOrchestrator(
        name="prism",
        gatekeeper=gk,
        planner=pl,
        gate_plan=gp,
        swarm=sw,
        ui_generator=ui,
        ui_filler_fast=ff,
        ui_filler_balanced=fb,
        ui_fixer=fx,
        # gk/pl are owned by gp; listing them again would double-assign their parent.
        sub_agents=[gp, sw, ui, ff, fb, fx],
    )


root_agent = build_root_agent()

app = App(root_agent=root_agent, name="app")
