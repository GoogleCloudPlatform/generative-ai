FROM python:3.12-slim-bullseye

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_CACHE=1
ENV UV_FROZEN=1
ENV UV_TOOL_BIN_DIR="/bin"
ENV PORT=8080

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y git && \
    uv tool install keyring --with keyrings.google-artifactregistry-auth && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the entire src directory to /app/src (maintaining structure)
COPY src /app/src

# Tell Python to look for modules inside /app/src
ENV PYTHONPATH=/app/src

# Copy pyproject.toml and uv.lock to the root of the app directory
COPY pyproject.toml uv.lock /app/


RUN --mount=type=secret,id=gcp \
GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcp \
uv sync --index-url https://pypi.org/simple

# Expose the PORT variable injected by Cloud Run and run the API on that port.
# Using 'sh -c' because the JSON type CMD doesn't unpack variables unless you use this.
CMD ["sh", "-c", "/app/.venv/bin/uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT}"]
