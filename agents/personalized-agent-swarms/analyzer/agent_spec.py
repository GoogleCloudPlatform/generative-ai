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

"""Read, write and run mini-agents as data, never as code.

Mini-agent files are written from LLM output, and that output is shaped by the
user's conversation history. Anyone who can put text into the history can steer
it (prompt injection), so the files must never be imported or executed.
Instead:

- parse_agent_source() reads only literal values of AGENT_META,
  ENRICHED_PROMPT and STEPS with ast.literal_eval. Everything else in the file
  (imports, functions, other statements) is ignored.
- render_agent_source() writes those values back as a data-only file.
- run_agent() is the one trusted execute() implementation. It does what the
  execute() template in the generation prompt does.
- load_agent() returns a module with that execute(), so callers work as before.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING, Any

import config as cfg
from google.genai import types

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from google import genai

# Top-level names read from an agent file. Nothing else in the file is used.
AGENT_VARS = ("AGENT_META", "ENRICHED_PROMPT", "STEPS")

# Same values as the execute() template in swarm_generator._AGENT_GEN_PROMPT.
HISTORY_TURNS = 6
MAX_PREVIOUS_OUTPUT_CHARS = 6000
MAX_OUTPUT_TOKENS = 65536
THINKING_BUDGET = 2048
FIRST_TURN_NOTE = (
    "Note: This is the FIRST message in this conversation. There is no prior "
    "context. Do not reference any previous discussion."
)

MAX_AGENT_NAME_CHARS = 100

_HEADER_TEXT = (
    "Mini-agent generated from conversation history (data only).\n"
    "\n"
    "This file is read with ast.literal_eval and is never imported or run, so\n"
    "any code added to it is ignored. Edit AGENT_META and ENRICHED_PROMPT (or\n"
    "STEPS) to change the agent. execute() is in analyzer/agent_spec.py.\n"
)

_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_]+")

_MISSING = object()


class InvalidAgentError(ValueError):
    """Raised when agent source has no usable literal prompt or steps."""


@dataclass(frozen=True)
class AgentSpec:
    """A mini-agent's data: metadata plus a prompt (static) or steps (dynamic).

    Attributes:
        meta: AGENT_META. Informational only; values are JSON-compatible.
        prompt: ENRICHED_PROMPT for a static agent, otherwise None.
        steps: STEPS for a dynamic agent, as dicts with "name" and "prompt",
            otherwise None.
    """

    meta: dict
    prompt: str | None = None
    steps: tuple[dict, ...] | None = None

    def __post_init__(self) -> None:
        """Check that exactly one of prompt and steps is set."""
        if (self.prompt is None) == (self.steps is None):
            raise InvalidAgentError("an agent needs exactly one of prompt or steps")


def parse_agent_source(source: str) -> AgentSpec:
    """Read an agent's data from its source text without running it.

    Only simple top-level assignments of literal values to AGENT_META,
    ENRICHED_PROMPT and STEPS are read, and the last one wins. A value that
    isn't a literal counts as missing. Everything else is ignored.

    Args:
        source: Text of an agent file. Treated as untrusted.

    Returns:
        The agent's metadata plus its prompt (static agent) or its steps
        (dynamic agent).

    Raises:
        InvalidAgentError: If the text isn't valid Python, or has neither a
            non-empty literal ENRICHED_PROMPT nor valid literal STEPS.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, MemoryError, RecursionError) as e:
        raise InvalidAgentError(f"not valid Python: {e}") from e

    values: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value_node = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value_node = node.target, node.value
        else:
            continue
        if not isinstance(target, ast.Name) or target.id not in AGENT_VARS:
            continue
        value = _eval_literal(value_node)
        if value is _MISSING:
            values.pop(target.id, None)
        else:
            values[target.id] = value

    raw_meta = values.get("AGENT_META")
    meta = _clean_meta(raw_meta) if isinstance(raw_meta, dict) else {}
    prompt = values.get("ENRICHED_PROMPT")
    if not isinstance(prompt, str) or not prompt.strip():
        prompt = None
    steps = _clean_steps(values.get("STEPS"))

    if steps is not None and (prompt is None or meta.get("complexity") == "dynamic"):
        return AgentSpec(meta=meta, steps=steps)
    if prompt is not None:
        return AgentSpec(meta=meta, prompt=prompt)
    raise InvalidAgentError("no literal ENRICHED_PROMPT or STEPS found")


def _eval_literal(node: ast.expr) -> object:
    """Evaluate a literal AST node, or return _MISSING if it isn't a literal."""
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, MemoryError, RecursionError):
        return _MISSING


def _json_compatible(value: object) -> object:
    """Return a JSON round-trip copy of value, or _MISSING if there isn't one."""
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError, RecursionError):
        return _MISSING


def _clean_meta(meta: dict) -> dict:
    """Keep metadata entries that have str keys and JSON-compatible values."""
    pairs = ((k, _json_compatible(v)) for k, v in meta.items() if isinstance(k, str))
    return {k: v for k, v in pairs if v is not _MISSING}


def _clean_steps(steps: object) -> tuple[dict, ...] | None:
    """Return steps as {"name", "prompt"} dicts, or None if any is malformed."""
    if not isinstance(steps, (list, tuple)) or not steps:
        return None
    clean = []
    for i, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            return None
        prompt = step.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            return None
        name = step.get("name")
        clean.append(
            {"name": name if isinstance(name, str) else f"step_{i}", "prompt": prompt}
        )
    return tuple(clean)


def render_agent_source(spec: AgentSpec) -> str:
    """Write an agent's data as Python source that contains only literals.

    The result is a docstring plus literal assignments, so importing it by
    mistake runs nothing, and parse_agent_source() reads it back unchanged.

    Args:
        spec: The agent's data.

    Returns:
        Source text for an agent file.
    """
    parts = [_str_literal(_HEADER_TEXT), f"AGENT_META = {_literal(spec.meta)}"]
    if spec.steps is not None:
        parts.append(f"STEPS = {_literal(list(spec.steps))}")
    else:
        parts.append(f"ENRICHED_PROMPT = {_literal(spec.prompt)}")
    return "\n\n".join(parts) + "\n"


def _literal(value: object, indent: int = 0) -> str:
    """Render a JSON-like value (str, number, bool, None, list, dict) as source."""
    if isinstance(value, str):
        return _str_literal(value)
    inner = " " * (indent + 4)
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = "".join(
            f"{inner}{_literal(k, indent + 4)}: {_literal(v, indent + 4)},\n"
            for k, v in value.items()
        )
        return "{\n" + items + " " * indent + "}"
    if isinstance(value, (list, tuple)):
        if not value:
            return "[]"
        items = "".join(f"{inner}{_literal(v, indent + 4)},\n" for v in value)
        return "[\n" + items + " " * indent + "]"
    return repr(value)


def _str_literal(text: str) -> str:
    """Render text as a readable string literal that evaluates back to text.

    Uses "..." for one line and triple quotes for several lines when no
    escaping is needed, and repr() otherwise. The result is checked with
    ast.literal_eval, so the text can never end the literal early.
    """
    if '"' not in text and "\\" not in text and text.isprintable():
        literal = f'"{text}"'
    elif (
        '"""' not in text
        and "\\" not in text
        and not text.endswith('"')
        and text.replace("\n", "").replace("\t", "").isprintable()
    ):
        literal = f'"""{text}"""'
    else:
        return repr(text)
    try:
        round_trips = ast.literal_eval(literal) == text
    except (SyntaxError, ValueError):
        round_trips = False
    return literal if round_trips else repr(text)


def sanitize_agent_source(source: str) -> str:
    """Rewrite agent source so that only the agent's data is kept.

    Args:
        source: Agent source text from the LLM. Treated as untrusted.

    Returns:
        Data-only source from render_agent_source().

    Raises:
        InvalidAgentError: If the source has no usable literal prompt or steps.
    """
    spec = parse_agent_source(source)
    rendered = render_agent_source(spec)
    if parse_agent_source(rendered) != spec:
        raise InvalidAgentError("agent data changed when re-rendered")
    return rendered


class AgentModule(ModuleType):
    """What load_agent() returns: an agent's data plus the trusted execute().

    Also has ENRICHED_PROMPT (static agent) or STEPS (dynamic agent).

    Attributes:
        AGENT_META: The agent's metadata.
        execute: ``async execute(user_message, llm_client, history=None)``.
    """

    AGENT_META: dict[str, Any]
    execute: Callable[..., Awaitable[str | None]]


def load_agent(path: Path, module_name: str | None = None) -> AgentModule:
    """Load an agent file as data and attach the trusted execute().

    The file is parsed, never imported. The returned module has the interface
    callers used before: AGENT_META, ENRICHED_PROMPT or STEPS, and
    ``async execute(user_message, llm_client, history=None)``.

    Args:
        path: Agent file to read.
        module_name: Name for the returned module. Defaults to the file stem.

    Returns:
        A module whose execute() runs the agent through run_agent().

    Raises:
        InvalidAgentError: If the file has no usable literal prompt or steps.
        OSError: If the file can't be read.
    """
    spec = parse_agent_source(path.read_text(encoding="utf-8"))

    async def execute(
        user_message: str,
        llm_client: genai.Client,
        history: list[dict] | None = None,
    ) -> str | None:
        return await run_agent(spec, user_message, llm_client, history)

    data: dict[str, Any] = {"AGENT_META": dict(spec.meta)}
    if spec.steps is not None:
        data["STEPS"] = [dict(step) for step in spec.steps]
    else:
        data["ENRICHED_PROMPT"] = spec.prompt
    module = AgentModule(module_name or path.stem)
    module.__dict__.update(data, __file__=str(path), execute=execute)
    return module


async def run_agent(
    spec: AgentSpec,
    user_message: str,
    llm_client: genai.Client,
    history: list[dict] | None = None,
) -> str | None:
    """Run an agent: fill in its prompt(s) and call the model.

    Does what the execute() template in swarm_generator._AGENT_GEN_PROMPT
    does: same history window, first-turn note, step chaining, model and
    generation config.

    Args:
        spec: The agent's data.
        user_message: The user's message, with any style prefix already added.
        llm_client: A google.genai client.
        history: Earlier turns as {"role", "content"} dicts, if any.

    Returns:
        The model's text for a static agent, or the last step's text for a
        dynamic agent.
    """
    if history:
        history_context = "Conversation so far:\n" + "\n".join(
            f"{t['role'].upper()}: {t['content']}" for t in history[-HISTORY_TURNS:]
        )
    else:
        history_context = FIRST_TURN_NOTE

    if spec.prompt is not None:
        prompt = spec.prompt.format(user_message=user_message, history=history_context)
        return await _generate(llm_client, prompt)

    outputs: list[Any] = []
    for i, step in enumerate(spec.steps or ()):
        prompt = step["prompt"].format(
            user_message=user_message,
            previous_output="\n".join(outputs)[:MAX_PREVIOUS_OUTPUT_CHARS],
            history=history_context if i == 0 else "",
        )
        outputs.append(await _generate(llm_client, prompt))
    return outputs[-1]


async def _generate(llm_client: genai.Client, prompt: str) -> str | None:
    """Call the agent model once with the fixed mini-agent generation config."""
    response = await llm_client.aio.models.generate_content(
        model=cfg.AGENT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=MAX_OUTPUT_TOKENS,
            thinking_config=types.ThinkingConfig(thinking_budget=THINKING_BUDGET),
        ),
    )
    return response.text


def safe_agent_name(name: object, default: str = "agent") -> str:
    """Return an agent name that is safe to use in a file path.

    Agent names come from LLM output and become paths like agents/{name}.py,
    so a name such as "../../analyzer/llm_util" could overwrite other files.
    Valid Python identifiers (what the prompts ask for) are returned unchanged.
    Anything else is reduced to letters, digits and underscores.

    Args:
        name: Proposed name, usually a str from LLM JSON. May be missing.
        default: Returned as is when nothing usable is left.

    Returns:
        A non-empty name with no path separators or dots.
    """
    text = "" if name is None else str(name)
    if text.isidentifier():
        return text
    text = _UNSAFE_NAME_CHARS.sub("_", text).strip("_")[:MAX_AGENT_NAME_CHARS]
    if not text:
        return default
    return f"agent_{text}" if text[0].isdigit() else text
