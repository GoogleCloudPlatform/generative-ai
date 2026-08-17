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

# Prism — one container that serves the UI and runs the ADK pipeline in-process.

FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /code

# Sources + lockfile. The uv.lock glob keeps the build working if it is absent,
# but committing it makes `--frozen` reproducible.
COPY pyproject.toml README.md uv.lock* ./
COPY ./app ./app
COPY ./frontend ./frontend
COPY ./serve.py ./serve.py
COPY ./.env.example ./.env.example

RUN uv sync --frozen --no-dev

# --- runtime config -----------------------------------------------------------
# The deployed service uses Gemini Enterprise Agent Platform with the runtime service account, so no API
# key is baked into the image. GOOGLE_CLOUD_PROJECT is deliberately NOT set here —
# it is supplied at deploy time (--set-env-vars), keeping the image
# project-agnostic. To run this image against the Gemini API instead, pass
#   -e GOOGLE_GENAI_USE_VERTEXAI=false -e GOOGLE_API_KEY=...
ENV GOOGLE_GENAI_USE_VERTEXAI=true \
    GOOGLE_CLOUD_LOCATION=global \
    PYTHONUNBUFFERED=1

EXPOSE 8080

# Cloud Run injects $PORT (defaults to 8080). serve.py reads PRISM_HOST/PRISM_PORT.
CMD ["sh", "-c", "PRISM_HOST=0.0.0.0 PRISM_PORT=${PORT:-8080} uv run python serve.py"]
