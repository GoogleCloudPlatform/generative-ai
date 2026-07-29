# Use the official extremely fast UV python image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Enable bytecode compilation for slightly faster startup times
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first to take advantage of Docker layer caching
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the application source code
COPY app /app/app
COPY README.md /app/README.md

# Sync the project (finalized setup)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev

# Final running container
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy the virtual environment and code from the builder stage
COPY --from=builder /app /app

# Expose port 8080 (default for Google Cloud Run)
EXPOSE 8080

# Ensure Python finds our app and travel_booking packages
ENV PYTHONPATH=/app/app
ENV PORT=8080

# Set default environment variables
ENV USE_LIVEKIT=true

# Run the FastAPI server
CMD ["/app/.venv/bin/python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
