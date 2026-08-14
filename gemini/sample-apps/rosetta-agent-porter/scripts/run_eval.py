"""Dev harness for Stage 5 (fidelity eval).

    uv run python scripts/run_eval.py <target_name> [source_cache_name]

Runs the fidelity-eval engine against a ported project in workspace/ported/.

It loads the mined inputs + agent_summary + analyses from the Stage 1-2 cache in
workspace/cache/<source>.json. NOTE: that cache is keyed by the SOURCE repo name
(e.g. `open_deep_research`), not the ported target name (e.g. `deep-research-adk`).
This script tries, in order:
  1. an explicit source cache name passed as the 2nd arg,
  2. workspace/cache/<target>.json  (target == source),
  3. workspace/cache/<target minus '-adk'>.json,
and falls back to the ported project's <target>.plan.json summary (or a generic
summary) so `evaluate_fidelity` can SYNTHESIZE inputs when nothing is cached.

Prints each eval_case as it completes, then the final FidelityReport JSON.
"""

import asyncio
import json
import sys
from pathlib import Path

from app import evalgen, intake

CACHE = intake.WORKSPACE / "cache"
DEFAULT = "react-agent-adk"


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:  # broad except on purpose
        return None


def _resolve_source_cache(
    target: str, source_arg: str | None
) -> tuple[dict | None, str]:
    """Find the Stage 1-2 analyses cache for `target`. Returns (cache_dict, label)."""
    candidates: list[str] = []
    if source_arg:
        candidates.append(
            source_arg[:-5] if source_arg.endswith(".json") else source_arg
        )
    candidates.append(target)
    if target.endswith("-adk"):
        candidates.append(target[: -len("-adk")])
    for name in candidates:
        d = _load_json(CACHE / f"{name}.json")
        if d and ("eval_inputs" in d or "agent_summary" in d):
            return d, f"{name}.json"
    return None, ""


def _summary_from_plan(target: str) -> str:
    """Best-effort agent_summary from a cached PortPlan (<target>.plan.json)."""
    plan = _load_json(CACHE / f"{target}.plan.json")
    if plan:
        return plan.get("summary") or plan.get("target_name") or ""
    return ""


async def main(target: str, source_arg: str | None):
    project = intake.PORTED_DIR / target
    if not project.exists():
        raise SystemExit(f"no ported project at {project}")

    cache, label = _resolve_source_cache(target, source_arg)
    if cache:
        mined_inputs = (cache.get("eval_inputs") or {}).get("inputs") or []
        agent_summary = cache.get("agent_summary", "")
        analyses = {
            k: cache.get(k)
            for k in (
                "analysis_graph",
                "analysis_tools",
                "analysis_state",
                "analysis_models",
            )
        }
        print(f"(source cache: {label})")
    else:
        mined_inputs = []
        agent_summary = _summary_from_plan(target) or f"An agent named {target}."
        analyses = {}
        print(
            "(no source cache found — inputs will be SYNTHESIZED from agent_summary; "
            "pass the source cache name as the 2nd arg to use mined inputs)"
        )

    print(f"target      : {target}")
    print(f"agent_summary: {agent_summary}")
    print(f"mined inputs : {len(mined_inputs)}")
    print("=" * 72)

    report = None
    n = 0
    async for ev in evalgen.evaluate_fidelity(
        project, mined_inputs, agent_summary, analyses
    ):
        if ev["type"] == "eval_case":
            n += 1
            d = ev["data"]
            print(f"\n[case {n}] verdict={d['verdict']} score={d['score']}")
            print(f"  input    : {d['input'][:120]}")
            print(f"  rationale: {d['rationale'][:300]}")
        elif ev["type"] == "fidelity":
            report = ev["data"]

    print("\n" + "=" * 72)
    print("FIDELITY REPORT:")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    target = args[0] if args else DEFAULT
    source_arg = args[1] if len(args) > 1 else None
    asyncio.run(main(target, source_arg))
