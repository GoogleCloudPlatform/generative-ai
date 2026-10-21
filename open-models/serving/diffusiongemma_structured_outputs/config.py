#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared environment and endpoint configuration for DiffusionGemma on vLLM."""

import os
import pathlib

import google.auth


def load_dotenv_defaults() -> None:
    """Loads default environment variables from a local .env file if present."""
    # Clear placeholder values injected by IDE .env loaders.
    if os.environ.get("GOOGLE_CLOUD_PROJECT") == "[your-project-id]":
        os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
    env_file = pathlib.Path(__file__).resolve().parent / ".env"
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val and val != "[your-project-id]":
            os.environ.setdefault(key, val)


def resolve_default_project() -> str | None:
    """Resolves project ID from env or Application Default Credentials."""
    if os.environ.get("GOOGLE_CLOUD_PROJECT") == "[your-project-id]":
        os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
    env_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if env_project:
        return env_project
    try:
        _, project = google.auth.default()
        return project
    except Exception:
        return None


load_dotenv_defaults()

# Google Cloud region where the online prediction endpoint is deployed.
REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
# Online prediction endpoint display name or numeric resource ID.
ENDPOINT_ID = os.environ.get(
    "DIFFUSIONGEMMA_ENDPOINT_NAME", "diffusiongemma-vllm"
)
# Hugging Face Hub repository ID from which vLLM downloads the model weights.
HF_MODEL_ID = os.environ.get(
    "DIFFUSIONGEMMA_MODEL_ID", "nvidia/diffusiongemma-26B-A4B-it-NVFP4"
)
# OpenAI-compatible model alias exposed by the vLLM /v1/chat/completions API.
SERVED_MODEL_NAME = os.environ.get(
    "DIFFUSIONGEMMA_SERVED_MODEL_NAME", "diffusiongemma-26b"
)
# Official upstream vLLM release image mirrored in Artifact Registry.
DEFAULT_IMAGE_TEMPLATE = (
    "us-docker.pkg.dev/{project}/containers/vllm-openai:v0.31.0"
)
