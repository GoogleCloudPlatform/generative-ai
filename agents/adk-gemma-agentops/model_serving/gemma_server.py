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

# ruff: noqa: INP001

"""Stage 1 local OpenAI-compatible Gemma server (`/v1/chat/completions`).

Keeps quantized Gemma weights warm in Apple Silicon unified memory (`mlx` or
PyTorch `mps`) on `http://127.0.0.1:8080/v1` so edits to `app/agent.py` reload
in under `0.5s` at `$0` cloud cost.

Usage:
    uv run python model_serving/gemma_server.py --engine mlx
"""

import argparse
import contextlib
import importlib.util
import json
import os
import pathlib
import platform
import sys
import time
import uuid
from collections.abc import Callable
from typing import Any

from dotenv import load_dotenv

load_dotenv()

GenerateFn = Callable[[str, int, float], tuple[str, int]]
_RAM_SMALL_GB = 12
_RAM_MEDIUM_GB = 22
_RAM_LARGE_GB = 40


def _get_tool_call_extractor() -> Callable[
    [str, list[dict[str, Any]]], tuple[str, list[dict[str, Any]]]
]:
    """Imports the shared tool-call parser without requiring `PYTHONPATH=.`."""
    repo_root = str(pathlib.Path(__file__).resolve().parents[1])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    # pylint: disable=import-outside-toplevel
    from app.tool_parser import extract_tool_calls_from_text  # noqa: PLC0415

    return extract_tool_calls_from_text


def configure_hf_auth() -> str | None:
    """Normalizes Hugging Face token env vars for gated Gemma weight downloads."""
    token = (
        os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_HUB_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    )
    if token:
        token = token.strip()
        os.environ["HF_TOKEN"] = token
        os.environ["HUGGINGFACE_HUB_TOKEN"] = token
    return token


def get_mac_ram_gb() -> float:
    """Returns detected physical unified memory in GiB (defaults to `16.0`)."""
    try:
        return (os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")) / (1024**3)
    except (ValueError, OSError, AttributeError):
        return 16.0


def recommend_model(ram_gb: float, engine: str) -> str:
    """Selects the largest Gemma checkpoint that fits safely in host memory."""
    if engine == "mlx":
        if ram_gb < _RAM_SMALL_GB:
            return "mlx-community/gemma-3-4b-it-4bit"
        return (
            "mlx-community/gemma-3-12b-it-4bit"
            if ram_gb < _RAM_MEDIUM_GB
            else "mlx-community/gemma-3-27b-it-4bit"
        )
    if ram_gb < _RAM_SMALL_GB:
        return "google/gemma-4-E2B-it"
    if ram_gb < _RAM_MEDIUM_GB:
        return "google/gemma-4-E4B-it"
    return (
        "google/gemma-4-12b-it"
        if ram_gb < _RAM_LARGE_GB
        else "google/gemma-4-26B-A4B-it"
    )


def detect_best_engine(requested_engine: str) -> str:
    """Resolves the local inference runtime (`'mlx'` on Apple Silicon, else `'mps'`)."""
    if requested_engine in ("mlx", "mps"):
        return requested_engine
    if (
        platform.system() == "Darwin"
        and platform.machine() == "arm64"
        and importlib.util.find_spec("mlx_lm") is not None
    ):
        return "mlx"
    return "mps"


def _load_mlx_generator(model_id: str) -> tuple[Any, GenerateFn]:
    """Loads an MLX quantized checkpoint and returns `(tokenizer, generate_fn)`."""
    # pylint: disable=import-outside-toplevel
    import mlx_lm  # noqa: PLC0415

    model, tokenizer = mlx_lm.load(model_id)

    def generate(
        prompt_str: str, max_tokens: int, temperature: float
    ) -> tuple[str, int]:
        try:
            # pylint: disable=import-outside-toplevel
            from mlx_lm.sample_utils import make_sampler  # noqa: PLC0415

            reply = mlx_lm.generate(
                model,
                tokenizer,
                prompt=prompt_str,
                max_tokens=max_tokens,
                verbose=False,
                sampler=make_sampler(temp=max(0.0, temperature)),
            )
        except (ImportError, TypeError):
            reply = mlx_lm.generate(
                model,
                tokenizer,
                prompt=prompt_str,
                max_tokens=max_tokens,
                verbose=False,
            )
        return reply.strip(), len(reply.split())

    return tokenizer, generate


def _load_mps_generator(model_id: str, hf_token: str | None) -> tuple[Any, GenerateFn]:
    """Loads a Hugging Face model on PyTorch MPS (or CPU fallback)."""
    # pylint: disable=import-outside-toplevel
    import torch  # noqa: PLC0415
    from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: PLC0415

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "mps" else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=hf_token)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=dtype, device_map=device, token=hf_token
    )
    model.eval()

    def generate(
        prompt_str: str, max_tokens: int, temperature: float
    ) -> tuple[str, int]:
        inputs = tokenizer(prompt_str, return_tensors="pt").to(device)
        gen_kwargs: dict[str, Any] = {
            **inputs,
            "max_new_tokens": max_tokens,
            "do_sample": temperature > 0.0,
        }
        if temperature > 0.0:
            gen_kwargs["temperature"] = temperature
        with torch.no_grad():
            output_ids = model.generate(**gen_kwargs)
        prompt_len = inputs.input_ids.shape[1]
        new_tokens = output_ids[0][prompt_len:]
        return tokenizer.decode(new_tokens, skip_special_tokens=True).strip(), len(
            new_tokens
        )

    return tokenizer, generate


def _normalize_messages(
    raw_messages: list[dict[str, Any]], tools: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """Normalizes OpenAI tool messages into alternating `user`/`assistant` turns."""
    messages: list[dict[str, str]] = []
    if tools:
        tool_names = [
            t.get("function", {}).get("name")
            for t in tools
            if isinstance(t, dict) and t.get("function", {}).get("name")
        ]
        first_tool = tool_names[0] if tool_names else "func"
        messages.append(
            {
                "role": "system",
                "content": (
                    "You have access to the following tools:\n"
                    f"{json.dumps(tools, indent=2)}\n"
                    "To call a tool, respond with a JSON tool call: "
                    '{"tool_call": {"name": "<name>", "arguments": {<args>}}} '
                    f"or invoke the function directly (e.g. {first_tool}(...))."
                ),
            }
        )

    for msg in raw_messages:
        raw_role = msg.get("role", "user")
        role = "user" if raw_role == "tool" else raw_role
        content = msg.get("content") or ""
        if isinstance(content, list):
            content = " ".join(
                p.get("text", "") for p in content if isinstance(p, dict)
            )
        if raw_role == "tool":
            content = f"Tool result for {msg.get('name') or 'tool'}: {content}"
        elif raw_role == "assistant" and msg.get("tool_calls"):
            fn = msg["tool_calls"][0].get("function", {})
            raw_args = fn.get("arguments") or {}
            if isinstance(raw_args, str):
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    raw_args = json.loads(raw_args)
            content = json.dumps(
                {"tool_call": {"name": fn.get("name"), "arguments": raw_args}}
            )

        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += f"\n\n{content}"
        else:
            messages.append({"role": role, "content": str(content)})
    return messages


def _render_chat_prompt(tokenizer: Any, messages: list[dict[str, str]]) -> str:
    """Applies Gemma's chat template, folding a leading `system` turn if needed."""
    try:
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    except Exception:
        if messages and messages[0]["role"] == "system" and len(messages) > 1:
            folded = list(messages[1:])
            folded[0] = {
                "role": folded[0]["role"],
                "content": f"{messages[0]['content']}\n\n{folded[0]['content']}",
            }
            return tokenizer.apply_chat_template(
                folded, tokenize=False, add_generation_prompt=True
            )
        raise


def serve_local(
    model_id: str, host: str, port: int, engine: str, hf_token: str | None
) -> None:
    """Loads Gemma weights once and runs an OpenAI-compatible FastAPI server."""
    # pylint: disable=import-outside-toplevel
    import uvicorn  # noqa: PLC0415
    from fastapi import FastAPI  # noqa: PLC0415

    print(f"Loading '{model_id}' ({engine.upper()})...")
    t0 = time.perf_counter()
    tokenizer, generate_fn = (
        _load_mlx_generator(model_id)
        if engine == "mlx"
        else _load_mps_generator(model_id, hf_token)
    )
    print(f"Model loaded in {time.perf_counter() - t0:.1f}s.")

    extract_tool_calls = _get_tool_call_extractor()
    app = FastAPI(title=f"Local Gemma {engine.upper()} Server")

    @app.get("/v1/models")
    async def list_models() -> dict[str, Any]:
        return {
            "object": "list",
            "data": [{"id": model_id, "object": "model", "owned_by": "local-mac"}],
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(body: dict[str, Any]) -> dict[str, Any]:
        tools = body.get("tools") or []
        max_tokens = int(body.get("max_tokens") or 512)
        raw_temp = body.get("temperature")
        temperature = float(raw_temp) if raw_temp is not None else 0.7

        messages = _normalize_messages(body.get("messages", []), tools)
        prompt_str = _render_chat_prompt(tokenizer, messages)
        reply_text, comp_tokens = generate_fn(prompt_str, max_tokens, temperature)

        message_payload: dict[str, Any] = {"role": "assistant", "content": reply_text}
        finish_reason = "stop"
        if tools:
            _, tool_calls = extract_tool_calls(reply_text, tools)
            if tool_calls:
                message_payload = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls,
                }
                finish_reason = "tool_calls"

        prompt_tokens = len(prompt_str.split())
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_id,
            "choices": [
                {
                    "index": 0,
                    "message": message_payload,
                    "finish_reason": finish_reason,
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": comp_tokens,
                "total_tokens": prompt_tokens + comp_tokens,
            },
        }

    print(f"Starting {engine.upper()} server on http://{host}:{port}/v1 ...")
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    """Parses CLI options, detects Apple Silicon hardware, and starts the server."""
    parser = argparse.ArgumentParser(
        description="Local Gemma OpenAI-compatible server for Apple Silicon."
    )
    parser.add_argument("--model", default="", help="Hugging Face model ID.")
    parser.add_argument("--engine", choices=["auto", "mlx", "mps"], default="auto")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    hf_token = configure_hf_auth()
    ram_gb = get_mac_ram_gb()
    engine = detect_best_engine(args.engine)
    model_id = (
        args.model
        or os.environ.get("GEMMA_MODEL_ID")
        or recommend_model(ram_gb, engine)
    )
    print(
        f"Gemma Server ({engine.upper()}) | Model: {model_id} | "
        f"RAM: {ram_gb:.1f}GB | Endpoint: http://{args.host}:{args.port}/v1 | "
        f"HF Token: {'Loaded' if hf_token else 'Not set'}"
    )
    serve_local(model_id, args.host, args.port, engine, hf_token)


if __name__ == "__main__":
    main()
