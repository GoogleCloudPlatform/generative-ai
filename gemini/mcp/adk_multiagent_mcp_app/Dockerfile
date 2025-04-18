FROM python:3.12-slim
SHELL ["/bin/ash", "-o", "pipefail", "-c"]
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl=="7.81.0-1ubuntu1.10"  \
    build-essential=="12.9ubuntu3" \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs=="20.11.1-1nodesource1" --no-install-recommends \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
# Change the working directory to the `app` directory
WORKDIR /app
COPY . /app
ENV PATH="/app/.venv/bin:$PATH"
RUN uv sync --frozen

CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
