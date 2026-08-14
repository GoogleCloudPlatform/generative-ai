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
"""read_skill_reference: on-demand retrieval of agents-cli ADK skill references.

This is how Rosetta's multi-agent system "uses the agents-cli skills inside ADK":
the planner/codegen agents pull authoritative ADK reference text into context when
the static grounding in their instructions isn't enough (graph workflows, the eval
dataset schema, deploy details). The allowlist is a hard security boundary — the
tool can only read these specific skill files (no path traversal, no arbitrary
disk reads driven by model input).
"""

from __future__ import annotations

import os

_SKILL_ROOT = os.path.realpath(
    os.path.expanduser(os.getenv("ROSETTA_SKILLS_ROOT", "~/.agents/skills"))
)


def _p(rel: str) -> str:
    return os.path.join(_SKILL_ROOT, rel)


_REFERENCES: dict[str, str] = {
    "adk_python": _p("google-agents-cli-adk-code/references/adk-python.md"),
    "adk_workflows": _p("google-agents-cli-adk-code/references/adk-workflows.md"),
    "adk_code_overview": _p("google-agents-cli-adk-code/SKILL.md"),
    "scaffold": _p("google-agents-cli-scaffold/SKILL.md"),
    "scaffold_flags": _p("google-agents-cli-scaffold/references/flags.md"),
    "workflow": _p("google-agents-cli-workflow/SKILL.md"),
    "commands": _p("google-agents-cli-workflow/references/commands.md"),
    "internals": _p("google-agents-cli-workflow/references/internals.md"),
    "samples": _p("google-agents-cli-workflow/references/samples.md"),
    "eval": _p("google-agents-cli-eval/SKILL.md"),
    "eval_dataset_schema": _p("google-agents-cli-eval/references/dataset_schema.md"),
    "eval_metrics": _p("google-agents-cli-eval/references/metrics-guide.md"),
    "eval_builtin_tools": _p("google-agents-cli-eval/references/builtin-tools-eval.md"),
    "deploy": _p("google-agents-cli-deploy/SKILL.md"),
    "deploy_agent_runtime": _p("google-agents-cli-deploy/references/agent-runtime.md"),
    "deploy_cloud_run": _p("google-agents-cli-deploy/references/cloud-run.md"),
}

_MAX_CHARS = 60_000


def read_skill_reference(topic: str) -> dict:
    """Read an authoritative agents-cli ADK reference document by topic.

    Use this to look up exact ADK API imports, orchestration patterns, the graph
    Workflow API, the eval dataset schema, scaffold flags, or deployment details
    when the static grounding in your instructions is not enough.

    Args:
        topic: One of the known reference topics. Known topics include
            'adk_python', 'adk_workflows', 'scaffold', 'scaffold_flags',
            'workflow', 'commands', 'internals', 'samples', 'eval',
            'eval_dataset_schema', 'eval_metrics', 'eval_builtin_tools',
            'deploy', 'deploy_agent_runtime', 'deploy_cloud_run'.

    Returns:
        dict with 'status' ('success'|'error'); on success also 'topic', 'path',
        'content'; on error 'message' and 'available_topics'.
    """
    path = _REFERENCES.get(topic)
    if path is None:
        return {
            "status": "error",
            "message": f"Unknown topic {topic!r}.",
            "available_topics": sorted(_REFERENCES),
        }
    real = os.path.realpath(path)
    if not real.startswith(_SKILL_ROOT + os.sep):
        return {"status": "error", "message": "Path escapes the skill root."}
    try:
        with open(real, encoding="utf-8") as fh:
            content = fh.read(_MAX_CHARS)
    except FileNotFoundError:
        return {
            "status": "error",
            "message": f"Reference not found on disk: {real}",
            "available_topics": sorted(_REFERENCES),
        }
    return {"status": "success", "topic": topic, "path": real, "content": content}


def skill_reference_available() -> bool:
    """True if the skill corpus is present on this machine (else run without the tool)."""
    return os.path.isdir(_SKILL_ROOT) and os.path.isfile(_REFERENCES["adk_python"])
