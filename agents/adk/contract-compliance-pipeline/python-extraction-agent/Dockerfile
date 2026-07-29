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

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install UV
ADD https://astral.sh/uv/install.sh /install.sh
RUN chmod -R 755 /install.sh && /install.sh && rm /install.sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock* ./
RUN uv venv .venv
ENV PATH="/app/.venv/bin:${PATH}"

COPY . .

# Sync dependencies after package sources are present
RUN uv pip install -e .

EXPOSE 8000

ENV HOST=0.0.0.0
ENV PORT=8000

# Runs standard FastAPI uvicorn listener
CMD ["uvicorn", "app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8000"]
