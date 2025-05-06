FROM python:3.12-slim
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Install bash alongside other dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl=7.88.1-10+deb12u12 \
    build-essential=12.9 \
    # Install NodeSource repo for Node.js 20.x
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    # Install pinned Node.js version
    && apt-get install -y --no-install-recommends \
    nodejs=20.19.0-1nodesource1 \
    # Clean up APT caches
    && apt-get clean && rm -rf /var/lib/apt/lists/*
# Change the working directory to the `app` directory
WORKDIR /app
COPY . /app
ENV PATH="/app/.venv/bin:$PATH"
RUN uv sync --frozen

CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
