# =============================================================================
# Prism — ask a science question, get an interactive explainer
#
# First run:
#   make setup     # check prerequisites, install deps, create .env
#   $EDITOR .env   # add a Gemini API key OR a Google Cloud project
#   make demo      # open the printed URL
# =============================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

HOST     ?= 127.0.0.1
PORT     ?= 8040
URL      := http://$(HOST):$(PORT)
PORTFILE := .prism-port

# ---- Cloud Run deploy (optional). Override on the CLI:
#      make deploy GCP_PROJECT=my-project GCP_REGION=us-central1
GCP_PROJECT ?=
GCP_REGION  ?= us-central1
SERVICE     ?= prism
IMAGE       ?= $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/prism/$(SERVICE):latest

.PHONY: help setup check install env demo serve run stop restart \
        test lint format clean deploy deploy-build deploy-status deploy-logs

help: ## Show this help
	@echo "Prism — ask a science question, get an interactive explainer"
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

check: ## Verify the required command-line tools are installed
	@missing=0; \
	for tool in uv; do \
		if command -v $$tool >/dev/null 2>&1; then \
			echo "  ok      $$tool"; \
		else \
			echo "  MISSING $$tool"; missing=1; \
		fi; \
	done; \
	if [ $$missing -ne 0 ]; then \
		echo ""; \
		echo "Install the missing tools and re-run 'make check'."; \
		echo "  uv: https://docs.astral.sh/uv/getting-started/installation/"; \
		exit 1; \
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

serve: ## Run Prism locally (Ctrl-C to stop)
	@if [ ! -f .env ]; then \
		echo "No .env found. Run 'make setup' first."; exit 1; \
	fi
	@echo "$(PORT)" > $(PORTFILE)
	@echo "Prism  ->  $(URL)      (Ctrl-C to stop)"
	PRISM_HOST=$(HOST) PRISM_PORT=$(PORT) uv run python serve.py

run: serve ## Alias for 'serve'

stop: ## Stop the server from the last run
	@if ! command -v lsof >/dev/null 2>&1; then \
		echo "  'make stop' needs lsof — stop the server with Ctrl-C instead."; exit 0; \
	fi
	@if [ -f $(PORTFILE) ]; then \
		p=$$(cat $(PORTFILE)); \
		pid=$$(lsof -ti tcp:$$p 2>/dev/null); \
		if [ -n "$$pid" ]; then kill $$pid 2>/dev/null && echo "  stopped port $$p"; \
		else echo "  nothing on port $$p"; fi; \
		rm -f $(PORTFILE); \
	else \
		echo "No $(PORTFILE) — nothing to stop."; \
	fi

restart: stop serve ## Stop the last run, then start fresh

test: ## Run unit tests
	uv run pytest tests/unit -q

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
# The deployed service uses Gemini Enterprise Agent Platform with the runtime service account, so no
# API key is needed in the container.
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
