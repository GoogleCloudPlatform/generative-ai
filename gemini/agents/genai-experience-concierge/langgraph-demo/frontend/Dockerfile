# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

# Install dependencies in builder step
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim as builder

# Default environment variables
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_CACHE_DIR=/root/.cache/uv

WORKDIR /app

# Copy the dependency code to the image.
COPY pyproject.toml uv.lock README.md LICENSE.txt ./

# Install dependencies.
RUN uv sync --frozen --no-dev --no-install-project --no-editable --python-preference only-system

# copy and install application package.
COPY concierge_ui ./concierge_ui/
RUN uv sync --frozen --no-dev --no-editable --python-preference only-system

FROM python:3.12-slim-bookworm AS server
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/concierge_ui /app/concierge_ui

WORKDIR /app

ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0 STREAMLIT_SERVER_PORT=8080

ENTRYPOINT [".venv/bin/streamlit", "run", "concierge_ui/server.py"]
