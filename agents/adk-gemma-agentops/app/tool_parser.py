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

"""Stdlib-only tool-call parser shared by `app/gemma_llm.py` and `gemma_server.py`.

Zero third-party dependencies so the local Apple Silicon server can parse
Gemma's raw text output without importing Google ADK.
"""

import ast
import contextlib
import json
import re
from collections.abc import Sequence
from typing import Any

_JSON_CALL_PATTERN = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
_FENCED_JSON_PATTERN = r"```(?:json)?\s*\{.*?\}\s*```"
_FENCED_CODE_PATTERN = r"```(?:[a-zA-Z0-9_\-]+)?\s*(.*?)\s*```"


def _safe_literal(node: ast.AST) -> Any:
    """Evaluates a literal AST node safely, falling back to source text."""
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return ast.unparse(node)


def _valid_tools_map(tools_payload: Sequence[Any]) -> dict[str, dict[str, Any]]:
    """Maps declared OpenAI tool names to their JSON Schema parameter dicts."""
    valid: dict[str, dict[str, Any]] = {}
    for tool in tools_payload:
        if not isinstance(tool, dict):
            continue
        fn = tool.get("function")
        if isinstance(fn, dict) and fn.get("name"):
            valid[fn["name"]] = fn.get("parameters") or {}
    return valid


def _format_tool_call(index: int, name: str, args: Any) -> dict[str, Any]:
    """Builds a normalized OpenAI `tool_calls` entry."""
    if isinstance(args, str):
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            args = json.loads(args)
    serialized = args if isinstance(args, str) else json.dumps(args)
    return {
        "id": f"call_{index}_{name}",
        "type": "function",
        "function": {"name": name, "arguments": serialized},
    }


def _extract_json_tool_calls(
    text: str, valid_tools: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Extracts JSON-encoded tool calls (`{"tool_call": ...}` or `{"name": ...}`)."""
    extracted: list[dict[str, Any]] = []
    for candidate in re.findall(_JSON_CALL_PATTERN, text, re.DOTALL):
        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        tool_call = data.get("tool_call") if "tool_call" in data else data
        if isinstance(tool_call, dict) and tool_call.get("name") in valid_tools:
            args = tool_call.get("arguments") or tool_call.get("parameters") or {}
            extracted.append(_format_tool_call(len(extracted), tool_call["name"], args))
    return extracted


def _extract_ast_calls_from_line(
    line: str, valid_tools: dict[str, dict[str, Any]], start_index: int
) -> list[dict[str, Any]]:
    """Parses Python-style function calls on a single line via `ast.parse`."""
    try:
        tree = ast.parse(line)
    except (SyntaxError, ValueError, TypeError):
        return []

    found: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        name = node.func.id
        if name == "print" or name not in valid_tools:
            continue
        param_names = list(valid_tools[name].get("properties", {}).keys())
        kwargs: dict[str, Any] = {
            param_names[idx]: _safe_literal(arg)
            for idx, arg in enumerate(node.args)
            if idx < len(param_names)
        }
        for kw in node.keywords:
            if kw.arg is not None:
                kwargs[kw.arg] = _safe_literal(kw.value)
        found.append(_format_tool_call(start_index + len(found), name, kwargs))
    return found


def extract_tool_calls_from_text(
    text: str, tools_payload: list[dict[str, Any]]
) -> tuple[str, list[dict[str, Any]]]:
    """Extracts structured OpenAI tool calls from raw Gemma assistant text.

    Supports both fenced JSON objects (`{"tool_call": ...}` or
    `{"name": ..., "arguments": ...}`) and Python-style function calls parsed
    safely via `ast.parse` (never `eval`).

    Args:
        text: Raw `message.content` returned by Gemma.
        tools_payload: OpenAI-formatted list of declared function tool schemas.

    Returns:
        Tuple of `(remaining_assistant_text, extracted_openai_tool_calls)`.
    """
    valid_tools = _valid_tools_map(tools_payload)
    if not valid_tools:
        return text, []

    json_calls = _extract_json_tool_calls(text, valid_tools)
    if json_calls:
        cleaned = re.sub(_FENCED_JSON_PATTERN, "", text, flags=re.DOTALL).strip()
        cleaned = re.sub(_JSON_CALL_PATTERN, "", cleaned, flags=re.DOTALL).strip()
        return cleaned, json_calls

    ast_calls: list[dict[str, Any]] = []
    code_blocks = re.findall(_FENCED_CODE_PATTERN, text, re.DOTALL)
    for block in code_blocks or [text]:
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if line:
                ast_calls.extend(
                    _extract_ast_calls_from_line(line, valid_tools, len(ast_calls))
                )

    if ast_calls:
        cleaned = re.sub(
            r"```(?:[a-zA-Z0-9_\-]+)?\s*.*?\s*```", "", text, flags=re.DOTALL
        ).strip()
        return cleaned, ast_calls

    return text, []
