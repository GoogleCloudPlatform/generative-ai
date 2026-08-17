# =============================================================================
# Rosetta — agents that port agents
#
# First run:
#   make setup     # check prerequisites, install deps, create .env
#   $EDITOR .env   # add a Gemini API key OR a Google Cloud project
#   make demo      # open the printed URL
#
# Two ports are used: the cockpit and the ported agent's ADK api_server.
# Override either:  make demo PORT=8030 PORTED_PORT=8060
# =============================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

HOST        ?= 127.0.0.1
PORT        ?= 8030
PORTED_PORT ?= 8060
URL         := http://$(HOST):$(PORT)
PORT_FILE   := .rosetta-ports

# ---- Cloud Run deploy (optional). Override on the CLI:
#      make deploy GCP_PROJECT=my-project GCP_REGION=us-central1
GCP_PROJECT ?=
GCP_REGION  ?= us-central1
SERVICE     ?= rosetta
IMAGE       ?= $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/rosetta/$(SERVICE):latest

.PHONY: help setup check install env demo serve run stop restart \
        port eval safety test test-all lint format clean \
        deploy deploy-build deploy-run deploy-status deploy-logs

help: ## Show this help
	@echo "Rosetta — agents that port agents"
	@echo ""
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "First time:  make setup  &&  \$$EDITOR .env  &&  make demo"

setup: check install env ## One-shot first-time setup (check tools, install, create .env)
	@echo ""
	@echo "Setup complete. Next:"
	@echo "  1. Edit .env and set EITHER GOOGLE_API_KEY (Gemini API / AI Studio)"
	@echo "     OR GOOGLE_CLOUD_PROJECT (Gemini Enterprise Agent Platform)."
	@echo "  2. make demo"

check: ## Verify the host tools are installed (uv, git)
	@missing=0; \
	for tool in uv git; do \
		if command -v $$tool >/dev/null 2>&1; then \
			echo "  ok      $$tool"; \
		else \
			echo "  MISSING $$tool"; missing=1; \
		fi; \
	done; \
	if [ $$missing -ne 0 ]; then \
		echo ""; \
		echo "Install the missing tools and re-run 'make check'."; \
		echo "  uv:  https://docs.astral.sh/uv/getting-started/installation/"; \
		echo "  git: https://git-scm.com/downloads"; \
		exit 1; \
	fi
	@# agents-cli is a project dependency, so `uv sync` installs it into .venv.
	@if [ -x .venv/bin/agents-cli ]; then \
		echo "  ok      agents-cli ($$(.venv/bin/agents-cli --version 2>&1 | tr -d '\n'))"; \
	else \
		echo "  pending agents-cli  (installed by 'make install')"; \
	fi

install: ## Install dependencies (uv sync)
	uv sync

env: ## Create .env from .env.example if it doesn't exist
	@if [ -f .env ]; then \
		echo "  .env already present — leaving it as-is."; \
	else \
		cp .env.example .env; \
		echo "  Created .env from .env.example — add your API key or project id."; \
	fi

demo: serve ## Start the demo (alias for 'serve')

serve: ## Run the Rosetta cockpit (Ctrl-C to stop)
	@if [ ! -f .env ]; then \
		echo "No .env found. Run 'make setup' first."; exit 1; \
	fi
	@echo "$(PORT) $(PORTED_PORT)" > $(PORT_FILE)
	@echo "Rosetta cockpit  ->  $(URL)"
	@echo "ported agent     ->  :$(PORTED_PORT)      (Ctrl-C to stop)"
	ROSETTA_HOST=$(HOST) ROSETTA_PORT=$(PORT) ROSETTA_PORTED_PORT=$(PORTED_PORT) uv run python serve.py

run: serve ## Alias for 'serve'

stop: ## Stop the cockpit + ported api_server from the last run
	@if [ -f $(PORT_FILE) ]; then \
		read p pp < $(PORT_FILE); \
		for port_num in $$p $$pp; do \
			pid=$$(lsof -ti tcp:$$port_num 2>/dev/null); \
			if [ -n "$$pid" ]; then kill $$pid 2>/dev/null && echo "  stopped port $$port_num"; \
			else echo "  nothing on port $$port_num"; fi; \
		done; \
		rm -f $(PORT_FILE); \
	else \
		echo "No $(PORT_FILE) — nothing to stop."; \
	fi

restart: stop serve ## Stop the last run, then start fresh

port: ## Headless port:  make port REPO=https://github.com/langchain-ai/react-agent.git
	@if [ -z "$(REPO)" ]; then echo "Usage: make port REPO=<git-url-or-path>"; exit 1; fi
	uv run python scripts/port.py $(REPO)

eval: ## Fidelity eval on a built port:  make eval TARGET=react-agent-adk
	@if [ -z "$(TARGET)" ]; then echo "Usage: make eval TARGET=<ported-name>"; exit 1; fi
	uv run python scripts/run_eval.py $(TARGET)

safety: ## Run the safety checks (reject non-agent repos + resist prompt injection)
	uv run python scripts/test_safety.py

test: ## Run unit tests
	uv run pytest tests/unit -q

test-all: ## Run unit + integration tests (integration calls the live model)
	uv run pytest tests/unit tests/integration -q

lint: ## Check lint + formatting (ruff, non-mutating)
	uv run --extra lint ruff check .
	uv run --extra lint ruff format --check .

format: ## Auto-format and fix (ruff)
	uv run --extra lint ruff format .
	uv run --extra lint ruff check --fix .

clean: ## Remove Python / test caches
	@find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache .ruff_cache
	@echo "Cleaned caches."

# ---- Optional: deploy to Cloud Run ------------------------------------------
# Requires GCP_PROJECT. The deployed service uses Gemini Enterprise Agent Platform with the runtime
# service account, so no API key is needed in the container.
deploy: ## Full deploy to Cloud Run:  make deploy GCP_PROJECT=my-project
	@if [ -z "$(GCP_PROJECT)" ]; then echo "Usage: make deploy GCP_PROJECT=<project-id>"; exit 1; fi
	PROJECT=$(GCP_PROJECT) REGION=$(GCP_REGION) SERVICE=$(SERVICE) IMAGE=$(IMAGE) bash scripts/deploy.sh

deploy-build: ## Build + push the container image only (Cloud Build)
	@if [ -z "$(GCP_PROJECT)" ]; then echo "Usage: make deploy-build GCP_PROJECT=<project-id>"; exit 1; fi
	gcloud builds submit --project=$(GCP_PROJECT) --region=$(GCP_REGION) \
		--config=deployment/cloudbuild.yaml --substitutions=_IMAGE=$(IMAGE) .

deploy-status: ## Show the deployed service URL + latest revision
	@gcloud run services describe $(SERVICE) --project=$(GCP_PROJECT) --region=$(GCP_REGION) \
		--format="value(status.url,status.latestReadyRevisionName)" || echo "not deployed yet"

deploy-logs: ## Tail recent logs from the deployed service
	gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="$(SERVICE)"' \
		--project=$(GCP_PROJECT) --freshness=1h --format="value(textPayload)" | tail -60
