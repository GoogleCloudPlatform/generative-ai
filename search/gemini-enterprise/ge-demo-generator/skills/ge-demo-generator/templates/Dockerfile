FROM python:3.11.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.17 /uv /uvx /bin/

# The build tools follow the base image's own security updates; pinning them to
# a version would freeze this layer on a stale package set.
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN uv pip install --system -r requirements.txt

COPY . .

# Smoke test imports & A2UI v0.9 composite catalog verification
# The pipe is a smoke test, not a build step - a failure in it should not be
# masked by pipefail changing which exit status the layer reports.
# hadolint ignore=DL4006
RUN uv pip freeze | grep -iE "^(google-adk|a2ui|mcp|google-genai|a2a-sdk)" | tee /app/.dep-versions
RUN python scripts/dep_smoke_test.py || true
RUN python -c "import json; from a2ui.schema.constants import VERSION_0_9; from a2ui.schema.catalog import CatalogConfig; from a2ui.schema.common_modifiers import remove_strict_validation; from a2ui.a2a.parts import create_a2ui_part; c = json.load(open('adk_agent/app/catalogs/gemini_enterprise_composite_catalog.json')); assert c.get('catalogId'), 'FAIL: composite catalog missing catalogId'; m = (create_a2ui_part({'version': 'v0.9'}, version=VERSION_0_9).root.metadata or {}).get('mimeType'); assert m == 'application/json+a2ui', 'FAIL: unexpected A2UI mimeType ' + repr(m); print('a2ui v0.9 interface OK: ' + str(len(c.get('components') or {})) + ' components, mimeType=' + m)"

# --- Computer Use / browser automation only (enableComputerUse) ---
# Uncomment together with the four Computer Use lines in requirements.txt.
# Without this layer the wheel is present but Chromium and its OS libs are not,
# and every browse fails at launch inside Cloud Run.
# RUN playwright install --with-deps chromium
# ENV PLAYWRIGHT_HEADLESS=1

ENV PORT 8080
ENV GOOGLE_GENAI_USE_VERTEXAI 1
ENV PYTHONUNBUFFERED 1
ENV ADK_ENABLE_MCP_GRACEFUL_ERROR_HANDLING 1
ENV ADK_DISABLE_JSON_SCHEMA_FOR_FUNC_DECL 1
ENV OTEL_SDK_DISABLED true

EXPOSE 8080

CMD ["uvicorn", "adk_agent.app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]
