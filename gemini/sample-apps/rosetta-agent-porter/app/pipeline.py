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
"""The Rosetta porting pipeline as an async generator of progress events.

    async for ev in port_repo(url):
        ev = {"type": "...", "data": {...}}

This single entrypoint powers the CLI harness, the parallel multi-repo tests, and
the SSE server. Heavy/blocking work (clone, scaffold, uv sync, verify, agents-cli)
runs in threads so the event stream stays responsive. The final "done" event
carries the summary (project path, verdict, fidelity, chat readiness).

Model policy: ONE model (3.7 Flash) for every stage — the parallel analysis swarm + intake AND
the planner/codegen/fixer brain (see app/config.py ROLE_MODEL).
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from pathlib import Path

from app import agents, build, codegen, config, intake, verify
from app.runtime import as_dict, run_agent


def _ev(t: str, **data) -> dict:
    return {"type": t, "data": data}


async def port_repo(
    url: str,
    *,
    reuse_clone: bool = True,
    do_verify: bool = True,
) -> AsyncGenerator[dict, None]:
    t0 = time.time()
    timings: dict[str, float] = {}

    # ---- 1. INTAKE ---------------------------------------------------------
    yield _ev("phase", phase="intake")
    yield _ev("repo", url=url)
    ts = time.time()
    name = intake.repo_name(url)
    repo = intake.SOURCE_DIR / name
    if not (reuse_clone and repo.exists() and any(repo.iterdir())):
        try:
            repo = await asyncio.to_thread(intake.clone_repo, url)
        except Exception as e:  # broad except on purpose
            yield _ev("error", message=f"clone failed: {e}")
            return
    manifest = await asyncio.to_thread(intake.build_manifest, repo)
    secrets = await asyncio.to_thread(intake.secret_scan, repo)
    if secrets:
        yield _ev(
            "warning",
            message=f"possible secrets in {secrets[:5]} (ignored, not copied to port)",
        )
    manifest_text = intake.manifest_block(repo, manifest)
    yield _ev(
        "repo_tree",
        tree=manifest["tree"],
        loc=manifest["total_loc"],
        files=manifest["n_code"],
    )

    st = await run_agent(agents.build_intake(), {"manifest_block": manifest_text})
    scan = as_dict(st.get("scope")) or {}
    timings["intake"] = round(time.time() - ts, 1)
    yield _ev(
        "framework",
        framework=scan.get("framework"),
        confidence=scan.get("confidence"),
        summary=scan.get("agent_summary", ""),
    )
    decision = scan.get("decision")
    if decision != "ok":
        yield _ev("declined", decision=decision, reason=scan.get("reason", ""))
        yield _ev("done", ok=False, reason=f"{decision}: {scan.get('reason', '')}")
        return

    blocks = await asyncio.to_thread(
        intake.build_source_blocks, repo, scan.get("files_to_analyze", []), manifest
    )

    # ---- 2. ANALYSIS SWARM (x6, parallel) ----------------------------------
    yield _ev("phase", phase="analyzing", workers=6)
    ts = time.time()
    seed = {
        "framework": scan.get("framework"),
        "agent_summary": scan.get("agent_summary", ""),
        "source_block": blocks["source_block"],
        "docs_block": blocks["docs_block"],
    }
    st = await run_agent(agents.build_analysis_swarm(), seed)
    timings["analysis"] = round(time.time() - ts, 1)
    analyses = {
        "framework": scan.get("framework"),
        "agent_summary": scan.get("agent_summary", ""),
        "analysis_graph": as_dict(st.get("analysis_graph")),
        "analysis_prompts": as_dict(st.get("analysis_prompts")),
        "analysis_tools": as_dict(st.get("analysis_tools")),
        "analysis_state": as_dict(st.get("analysis_state")),
        "analysis_models": as_dict(st.get("analysis_models")),
        "eval_inputs": as_dict(st.get("eval_inputs")),
    }
    for facet in (
        "analysis_graph",
        "analysis_tools",
        "analysis_state",
        "analysis_models",
    ):
        yield _ev("analysis", facet=facet, data=analyses[facet])
    yield _ev("eval_inputs", data=analyses["eval_inputs"])

    # ---- 3. PORT PLAN / IR (SMART) -----------------------------------------
    yield _ev("phase", phase="planning")
    ts = time.time()
    st = await run_agent(
        agents.build_port_planner(),
        {
            "framework": analyses["framework"],
            "agent_summary": analyses["agent_summary"],
            "analyses_block": codegen.analyses_block(analyses),
        },
    )
    plan = as_dict(st.get("port_plan"))
    timings["planning"] = round(time.time() - ts, 1)
    if not plan or not plan.get("agents"):
        yield _ev("error", message="planner produced no PortPlan")
        yield _ev("done", ok=False, reason="planner failed")
        return
    yield _ev(
        "mapping",
        target_name=plan["target_name"],
        summary=plan.get("summary", ""),
        agents=plan["agents"],
        mappings=plan.get("mappings", []),
        risks=plan.get("risks", []),
    )

    # ---- 4. SCAFFOLD (agents-cli) ------------------------------------------
    yield _ev("phase", phase="scaffolding")
    ts = time.time()
    target = plan["target_name"]
    project, run = await asyncio.to_thread(build.scaffold_project, target)
    if not run.ok:
        yield _ev("error", message=f"scaffold failed: {run.text[-400:]}")
        yield _ev("done", ok=False, reason="scaffold failed")
        return
    await asyncio.to_thread(build.write_env, project)
    yield _ev("scaffold", name=target, path=str(project))

    # ---- 5. CODEGEN (SMART, delimited files) -------------------------------
    yield _ev("phase", phase="codegen")
    st = await run_agent(
        agents.build_codegen(),
        {
            "framework": analyses["framework"],
            "agent_summary": analyses["agent_summary"],
            "port_plan_block": json.dumps(plan, indent=2),
            "prompts_block": codegen.prompts_block(analyses),
            "analyses_block": codegen.analyses_block(analyses),
        },
    )
    files = codegen.parse_files(st.get("generated_raw") or "")
    timings["codegen"] = round(time.time() - ts, 1)
    if not files:
        yield _ev("error", message="codegen produced no parseable files")
        yield _ev("done", ok=False, reason="codegen failed")
        return
    await asyncio.to_thread(build.apply_files, project, files)
    for f in files:
        yield _ev("file", path=f.path, loc=f.content.count("\n") + 1)

    # deps for the ported project (needed for lint + import + run)
    yield _ev("phase", phase="installing")
    ts = time.time()
    # Domain libraries the source leaned on (python-chess, a parser, a solver).
    # Without these the generator reimplements them under app/ and gets them
    # subtly wrong; the names are validated in build.read_extra_deps.
    added, rejected, dep_err = await asyncio.to_thread(build.apply_extra_deps, project)
    if added or rejected or dep_err:
        yield _ev("deps", added=added, rejected=rejected, error=dep_err)
    await asyncio.to_thread(build.acli_install_or_sync, project)
    timings["install"] = round(time.time() - ts, 1)

    # ---- 6. VERIFY + SELF-HEAL ---------------------------------------------
    verdict = None
    repairs = 0
    if do_verify:
        yield _ev("phase", phase="verifying")
        ts = time.time()
        verdict = await asyncio.to_thread(verify.static_check, project)
        while not verdict.ok and repairs < config.MAX_REPAIRS:
            yield _ev("repair", n=repairs + 1, errors=verdict.errors)
            heal = await run_agent(
                agents.build_fixer(),
                {
                    "verdict_errors": "\n".join(verdict.errors),
                    "broken_block": codegen.broken_block(files),
                },
            )
            patch = codegen.parse_files(heal.get("fixed_raw") or "")
            if not patch:
                break
            files = build.merge_files(files, patch)
            await asyncio.to_thread(build.apply_files, project, files)
            for f in patch:
                yield _ev(
                    "file", path=f.path, loc=f.content.count("\n") + 1, patched=True
                )
            # A repair may add a missing domain library (the classic
            # ModuleNotFoundError fix). Re-run this every round so the manifest is
            # installed AND consumed — otherwise it would linger, uninstalled, in
            # the delivered project.
            r_added, r_rejected, r_err = await asyncio.to_thread(
                build.apply_extra_deps, project
            )
            if r_added or r_rejected or r_err:
                yield _ev("deps", added=r_added, rejected=r_rejected, error=r_err)
            verdict = await asyncio.to_thread(verify.static_check, project)
            repairs += 1
        timings["verify"] = round(time.time() - ts, 1)
        yield _ev("verify", ok=verdict.ok, errors=verdict.errors, repairs=repairs)

    # ---- done --------------------------------------------------------------
    timings["total"] = round(time.time() - t0, 1)
    ok = verdict.ok if verdict else True
    yield _ev(
        "metrics",
        timings_s=timings,
        files=len(files),
        repairs=repairs,
        risks=len(plan.get("risks", [])),
    )
    yield _ev(
        "done",
        ok=ok,
        project=str(project),
        target_name=target,
        build_green=(verdict.ok if verdict else None),
        repairs=repairs,
    )


# persist the final fileset to cache after a run (used by other stages)
def cache_files(name: str, files) -> None:
    cache = intake.WORKSPACE / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / f"{name}.code_files.json").write_text(
        json.dumps([f.model_dump() for f in files], indent=2)
    )


def _project_path(name: str) -> Path:
    return intake.PORTED_DIR / name
