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

"""Zero-proxy Google ADK `BaseLlm` adapter for local and Gemini Agent Platform MaaS Gemma.

Supports the two serving backends without third-party LLM proxy dependencies:
- Local Apple Silicon server (`AGENT_ENV=dev`, `model_serving/gemma_server.py`)
  over OpenAI-compatible `/v1/chat/completions`.
- Serverless Gemini Agent Platform Gemma 4 MaaS (`AGENT_ENV=staging|prod`, `global`
  endpoint `google/gemma-4-26b-a4b-it-maas`) with native OpenAI tool calling,
  cached ADC bearer auth, and exponential-backoff retries on transient 429/5xx.
"""

import asyncio
import json
import os
import re
import time
from collections.abc import AsyncGenerator
from typing import Any

import google.auth
import google.auth.transport.requests
import httpx
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from app.tool_parser import extract_tool_calls_from_text

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_GCP_TOKEN_TTL_SECONDS = 1800.0

_RUNTIME_CACHE: dict[str, Any] = {
    "client": None,
    "token": "",
    "token_ts": 0.0,
    "default_project": "",
}


def resolve_project_id(fallback: str = "") -> str:
    """Resolves the active Google Cloud project ID from standard env vars."""
    return (
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT_ID")
        or os.environ.get("PROJECT_ID")
        or fallback
    )


def _get_http_client() -> httpx.AsyncClient:
    """Returns a shared connection-pooled `httpx.AsyncClient`."""
    client: httpx.AsyncClient | None = _RUNTIME_CACHE["client"]
    if client is None or client.is_closed:
        limits = httpx.Limits(max_connections=200, max_keepalive_connections=100)
        client = httpx.AsyncClient(timeout=60.0, limits=limits)
        _RUNTIME_CACHE["client"] = client
    return client


def _get_gcp_token() -> tuple[str, str]:
    """Acquires and caches an OAuth2 bearer token via Application Default Credentials."""
    now = time.monotonic()
    cached_token: str = _RUNTIME_CACHE["token"]
    cached_ts: float = _RUNTIME_CACHE["token_ts"]
    if cached_token and (now - cached_ts) < _GCP_TOKEN_TTL_SECONDS:
        return cached_token, str(_RUNTIME_CACHE["default_project"])

    creds, default_project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    token = creds.token or ""
    project = default_project or ""
    _RUNTIME_CACHE["token"] = token
    _RUNTIME_CACHE["token_ts"] = now
    _RUNTIME_CACHE["default_project"] = project
    return token, project


def _lowercase_schema_types(obj: Any) -> Any:
    """Converts uppercase Google Gen AI schema type enums to OpenAI lowercase."""
    if isinstance(obj, dict):
        return {
            k: (
                v.lower()
                if k == "type" and isinstance(v, str)
                else [t.lower() if isinstance(t, str) else t for t in v]
                if k == "type" and isinstance(v, list)
                else _lowercase_schema_types(v)
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_lowercase_schema_types(item) for item in obj]
    return obj


def _serialize_tool_response(resp_val: Any) -> str:
    """Serializes an ADK `FunctionResponse.response` payload as a JSON string."""
    if isinstance(resp_val, str):
        return resp_val
    try:
        return json.dumps(resp_val)
    except (TypeError, ValueError):
        return str(resp_val)


def _strip_thought_blocks(text: str) -> str:
    """Removes internal `<thought>` / `<think>` blocks emitted by reasoning models."""
    cleaned = re.sub(r"<(thought|think)>.*?</\1>", "", text, flags=re.DOTALL).strip()
    return re.sub(r"<(thought|think)>.*$", "", cleaned, flags=re.DOTALL).strip()


def _resolve_local_chat_url(api_base: str) -> str:
    """Normalizes a local base URL to an OpenAI `/chat/completions` URL."""
    base = api_base.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


async def _post_json_with_retry(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    *,
    max_attempts: int,
) -> dict[str, Any]:
    """POSTs a JSON request with exponential backoff on transient 429/5xx errors."""
    client = _get_http_client()
    attempts = max(1, max_attempts)
    for attempt in range(attempts):
        try:
            resp = await client.post(url, headers=headers, json=payload)
        except httpx.RequestError:
            if attempt < attempts - 1:
                await asyncio.sleep(1.5 * (2**attempt))
                continue
            raise
        if resp.status_code in _RETRYABLE_STATUS_CODES and attempt < attempts - 1:
            await asyncio.sleep(1.5 * (2**attempt))
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Exhausted {attempts} attempts calling {url}")


class GemmaEndpointLlm(BaseLlm):
    """Google ADK `BaseLlm` adapter for local and Gemini Agent Platform MaaS Gemma endpoints.

    Attributes:
        model: Model identifier string (e.g. `google/gemma-4-26b-a4b-it-maas`).
        api_base: Base HTTP URL for the local OpenAI-compatible dev server.
        use_maas: When `True`, calls Gemini Agent Platform's serverless `global`
            OpenAI-compatible endpoint with native `tools`/`tool_calls`.
        max_tokens: Maximum completion tokens generated per turn.
        temperature: Sampling temperature (`0.1` favors deterministic tool args).
        num_retries: Maximum exponential-backoff attempts on transient 429/5xx.
    """

    model: str
    api_base: str = ""
    use_maas: bool = False
    max_tokens: int = 1024
    temperature: float = 0.1
    num_retries: int = 4

    def _extract_tools_payload(self, llm_request: LlmRequest) -> list[dict[str, Any]]:
        """Converts ADK `FunctionDeclaration` schemas to OpenAI `tools` payloads."""
        tools_payload: list[dict[str, Any]] = []
        if not (llm_request.config and llm_request.config.tools):
            return tools_payload
        for tool_obj in llm_request.config.tools:
            for decl in getattr(tool_obj, "function_declarations", None) or []:
                raw_params = (
                    decl.parameters.model_dump(exclude_none=True)
                    if getattr(decl, "parameters", None)
                    else {"type": "object", "properties": {}}
                )
                tools_payload.append(
                    {
                        "type": "function",
                        "function": {
                            "name": decl.name,
                            "description": decl.description or "",
                            "parameters": _lowercase_schema_types(raw_params),
                        },
                    }
                )
        return tools_payload

    def _convert_llm_request_maas(
        self, llm_request: LlmRequest
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Converts an ADK `LlmRequest` into native OpenAI messages for Gemini Agent Platform MaaS."""
        tools_payload = self._extract_tools_payload(llm_request)
        messages: list[dict[str, Any]] = []

        raw_inst = llm_request.config.system_instruction if llm_request.config else None
        if isinstance(raw_inst, str) and raw_inst.strip():
            messages.append({"role": "system", "content": raw_inst.strip()})

        for content in llm_request.contents or []:
            parts = content.parts or []
            texts = [p.text for p in parts if getattr(p, "text", None)]
            calls = [
                p.function_call for p in parts if getattr(p, "function_call", None)
            ]
            responses = [
                p.function_response
                for p in parts
                if getattr(p, "function_response", None)
            ]

            if responses:
                for idx, fr in enumerate(responses):
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": getattr(fr, "id", None)
                            or f"call_{idx}_{fr.name or 'func'}",
                            "name": fr.name or "",
                            "content": _serialize_tool_response(fr.response),
                        }
                    )
            elif content.role == "model" and calls:
                oa_calls = [
                    {
                        "id": getattr(fc, "id", None)
                        or f"call_{idx}_{fc.name or 'func'}",
                        "type": "function",
                        "function": {
                            "name": fc.name or "",
                            "arguments": json.dumps(fc.args or {}),
                        },
                    }
                    for idx, fc in enumerate(calls)
                ]
                messages.append(
                    {
                        "role": "assistant",
                        "content": "\n".join(texts) if texts else None,
                        "tool_calls": oa_calls,
                    }
                )
            elif texts:
                role = "assistant" if content.role == "model" else "user"
                messages.append({"role": role, "content": "\n".join(texts)})

        return messages, tools_payload

    @staticmethod
    def _format_local_tool_prompt(tools_payload: list[dict[str, Any]]) -> str:
        """Builds an inline tool-calling prompt for local Jinja templates."""
        if not tools_payload:
            return ""
        descs = []
        for tool in tools_payload:
            fn = tool["function"]
            props = fn.get("parameters", {}).get("properties", {})
            sig = ", ".join(f"{p}: {v.get('type', 'any')}" for p, v in props.items())
            descs.append(f"- {fn['name']}({sig}): {fn.get('description', '')}")
        return (
            "You have access to the following tools:\n"
            + "\n".join(descs)
            + "\n\nWhen you need to call a tool, respond ONLY with a JSON object:\n"
            '```json\n{"name": "<tool_name>", "arguments": {<arguments>}}\n```'
        )

    @staticmethod
    def _merge_alternating_turns(
        raw_messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merges adjacent same-role turns so Gemma templates strictly alternate."""
        normalized: list[dict[str, Any]] = []
        for msg in raw_messages:
            if not msg.get("content"):
                continue
            if normalized and normalized[-1]["role"] == msg["role"]:
                normalized[-1]["content"] += "\n\n" + msg["content"]
            else:
                normalized.append(msg)
        return normalized

    @staticmethod
    def _content_to_local_message(
        content: types.Content,
    ) -> tuple[dict[str, Any] | None, bool]:
        """Converts one ADK `Content` block into a local-server message dict."""
        parts = content.parts or []
        texts = [p.text for p in parts if getattr(p, "text", None)]
        calls = [p.function_call for p in parts if getattr(p, "function_call", None)]
        responses = [
            p.function_response for p in parts if getattr(p, "function_response", None)
        ]
        if responses:
            lines = [
                f"Tool '{fr.name or ''}' returned: {_serialize_tool_response(fr.response)}"
                for fr in responses
            ]
            body = (
                "\n".join(lines)
                + "\n\nProvide the final answer concisely based on this result."
            )
            return {"role": "user", "content": body}, True
        if content.role == "model" and calls and not texts:
            fc = calls[0]
            body = json.dumps({"name": fc.name or "", "arguments": fc.args or {}})
            return {"role": "assistant", "content": f"```json\n{body}\n```"}, False
        if texts:
            role = "assistant" if content.role == "model" else "user"
            return {"role": role, "content": "\n".join(texts)}, False
        return None, False

    def _convert_llm_request_local(
        self, llm_request: LlmRequest
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Converts an ADK `LlmRequest` into strictly alternating local Gemma turns.

        Gemma's local Jinja template rejects standalone `system` messages and
        requires alternating `user` / `assistant` turns.
        """
        tools_payload = self._extract_tools_payload(llm_request)
        raw_inst = llm_request.config.system_instruction if llm_request.config else None
        sys_text = raw_inst.strip() if isinstance(raw_inst, str) else ""

        raw_messages: list[dict[str, Any]] = []
        has_tool_response = False
        for content in llm_request.contents or []:
            msg, saw_resp = self._content_to_local_message(content)
            has_tool_response = has_tool_response or saw_resp
            if msg is not None:
                raw_messages.append(msg)

        # Inject tool instructions on Turn 1 only so Turn 2 synthesizes prose.
        tool_prompt = (
            "" if has_tool_response else self._format_local_tool_prompt(tools_payload)
        )
        preamble = [p for p in (sys_text, tool_prompt) if p]
        if preamble:
            prefix = "\n\n".join(preamble)
            for msg in raw_messages:
                if msg["role"] == "user":
                    msg["content"] = f"{prefix}\n\n{msg['content']}".strip()
                    break
            else:
                raw_messages.insert(0, {"role": "user", "content": prefix})

        return self._merge_alternating_turns(raw_messages), tools_payload

    @staticmethod
    def _tool_call_to_part(index: int, tool_call: dict[str, Any]) -> types.Part:
        """Converts one OpenAI `tool_calls` entry into an ADK `FunctionCall` part."""
        fn = tool_call.get("function") or {}
        fn_name = fn.get("name") or ""
        raw_args = fn.get("arguments") or "{}"
        parsed_args: dict[str, Any] = {}
        if isinstance(raw_args, str):
            try:
                parsed = json.loads(raw_args)
                if isinstance(parsed, dict):
                    parsed_args = parsed
            except (json.JSONDecodeError, TypeError, ValueError):
                parsed_args = {}
        elif isinstance(raw_args, dict):
            parsed_args = raw_args
        return types.Part(
            function_call=types.FunctionCall(
                id=tool_call.get("id") or f"call_{index}_{fn_name or 'func'}",
                name=fn_name,
                args=parsed_args,
            )
        )

    def _build_llm_response(
        self, response_json: dict[str, Any], tools_payload: list[dict[str, Any]]
    ) -> LlmResponse:
        """Converts an OpenAI chat completion JSON payload into an ADK `LlmResponse`."""
        choices = response_json.get("choices") or []
        message = (choices[0].get("message") if choices else None) or {}
        raw_text = message.get("content")
        tool_calls = list(message.get("tool_calls") or [])

        if not tool_calls and isinstance(raw_text, str) and raw_text.strip():
            cleaned_text, parsed_calls = extract_tool_calls_from_text(
                raw_text, tools_payload
            )
            if parsed_calls:
                tool_calls, raw_text = parsed_calls, cleaned_text

        out_parts: list[types.Part] = []
        if isinstance(raw_text, str) and raw_text.strip():
            cleaned = _strip_thought_blocks(raw_text)
            if cleaned:
                out_parts.append(types.Part.from_text(text=cleaned))

        out_parts.extend(
            self._tool_call_to_part(idx, tc) for idx, tc in enumerate(tool_calls)
        )
        if not out_parts:
            fallback = (
                raw_text.strip()
                if isinstance(raw_text, str) and raw_text.strip()
                else "I have completed processing your request."
            )
            out_parts.append(types.Part.from_text(text=fallback))

        usage = response_json.get("usage")
        usage_meta = (
            types.GenerateContentResponseUsageMetadata(
                prompt_token_count=int(usage.get("prompt_tokens", 0)),
                candidates_token_count=int(usage.get("completion_tokens", 0)),
                total_token_count=int(usage.get("total_tokens", 0)),
            )
            if isinstance(usage, dict)
            else None
        )
        return LlmResponse(
            content=types.Content(role="model", parts=out_parts),
            partial=False,
            finish_reason=types.FinishReason.STOP,
            usage_metadata=usage_meta,
        )

    async def generate_content_async(
        self,
        llm_request: LlmRequest,
        stream: bool = False,
    ) -> AsyncGenerator[LlmResponse]:
        """Executes a chat completion against Gemma and yields a single `LlmResponse`."""
        del stream  # Emits a single unary completion.
        if self.use_maas:
            messages, tools_payload = self._convert_llm_request_maas(llm_request)
            token, default_project = _get_gcp_token()
            project_id = resolve_project_id(default_project)
            url = (
                "https://aiplatform.googleapis.com/v1/projects/"
                f"{project_id}/locations/global/endpoints/openapi/chat/completions"
            )
            headers = {"Authorization": f"Bearer {token}"}
            if project_id:
                headers["x-goog-user-project"] = project_id
            max_attempts = self.num_retries
        else:
            messages, tools_payload = self._convert_llm_request_local(llm_request)
            url = _resolve_local_chat_url(self.api_base)
            api_key = os.environ.get("GEMMA_API_KEY", "local-no-key-required")
            headers = {"Authorization": f"Bearer {api_key}"}
            max_attempts = 1

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }
        if tools_payload:
            payload["tools"] = tools_payload

        response_json = await _post_json_with_retry(
            url, payload, headers, max_attempts=max_attempts
        )
        yield self._build_llm_response(response_json, tools_payload)
