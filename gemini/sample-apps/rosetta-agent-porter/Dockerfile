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

# Rosetta — a single container that runs the whole app on Cloud Run.
#
# Unlike a normal ADK service, Rosetta's serve.py doesn't just serve a UI: it
# runs a porting pipeline that shells out to the toolchain, so this ONE image
# must carry the whole toolchain, not just Python deps:
#   - git         : app/intake.py clones source repos (`git clone --depth 1`).
#   - uv          : app/acli.py runs `uv sync` / `uv run adk api_server` per port.
#   - agents-cli  : app/acli.py invokes bare `agents-cli` (scaffold/install/lint/eval).
#   - the app     : serve.py + app/ + frontend/ + the rosetta venv (google-adk, ...).
# serve.py also spawns a child `adk api_server` (via uv) and proxies chat to it.

FROM python:3.12-slim

# --- OS deps: git (repo intake) + curl/ca-certificates (TLS + fetches) --------
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# --- uv: drives per-port `uv sync` and `uv run adk api_server` -----------------
RUN pip install --no-cache-dir uv==0.8.13

# --- agents-cli on PATH as a bare command (app/acli.py calls `agents-cli`) -----
# `uv tool install` drops the launcher into the uv tool bin dir (~/.local/bin);
# put that on PATH so `agents-cli` resolves without a full path.
ENV PATH="/root/.local/bin:${PATH}"
RUN uv tool install google-agents-cli

WORKDIR /code

# App sources + lockfile (uv.lock optional via the glob so the build won't fail
# if it's absent, but committing it keeps `--frozen` reproducible).
COPY pyproject.toml README.md uv.lock* ./
COPY ./app ./app
COPY ./frontend ./frontend
COPY ./serve.py ./serve.py
COPY ./.env.example ./.env.example

# Install rosetta's own deps (google-adk, fastapi, ...) into /code/.venv. This
# ALSO warms the shared uv cache in the image, so the per-port `uv sync` of each
# freshly-ported project links from cache instead of re-downloading. Keep the
# default uv cache in the image (do NOT set UV_NO_CACHE).
RUN uv sync --frozen --no-dev

# --- runtime config -----------------------------------------------------------
# The deployed service uses Gemini Enterprise Agent Platform with the runtime service account, so no API
# key is needed in the image. GOOGLE_CLOUD_PROJECT is deliberately NOT baked in —
# it is supplied at deploy time (--set-env-vars), keeping the image project-agnostic.
# To run this image against the Gemini API instead, pass
#   -e ROSETTA_BACKEND=ai-studio -e GOOGLE_API_KEY=...
ENV ROSETTA_BACKEND=agent-platform \
    GOOGLE_CLOUD_LOCATION=global \
    ROSETTA_WORKSPACE=/tmp/rosetta-workspace \
    PYTHONUNBUFFERED=1

EXPOSE 8080

# Cloud Run injects $PORT (defaults to 8080). serve.py reads ROSETTA_HOST /
# ROSETTA_PORT, so bind 0.0.0.0:$PORT here. Pre-create the writable workspace
# (/tmp is writable on Cloud Run) before starting the server.
CMD ["sh", "-c", "mkdir -p \"$ROSETTA_WORKSPACE\" && ROSETTA_HOST=0.0.0.0 ROSETTA_PORT=${PORT:-8080} uv run python serve.py"]
