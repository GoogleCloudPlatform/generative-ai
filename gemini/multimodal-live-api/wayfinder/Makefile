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

SHELL     := /bin/bash
VENV      := .venv
PY        := $(VENV)/bin/python
PIP       := $(VENV)/bin/pip
PORT      ?= 8080
IMAGE     ?= wayfinder:dev
ENV_FILE  ?= .env
H2C       := widget/third_party/html2canvas/html2canvas.min.js

.DEFAULT_GOAL := help
.PHONY: help install run test docker-build docker-run deploy demo-docs provision provision-docs clean

help:
	@awk 'BEGIN{FS=":.*##"; printf "Wayfinder targets:\n"} /^[a-zA-Z_-]+:.*?##/ {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@touch $(VENV)/bin/activate

$(H2C):
	python3 scripts/fetch_html2canvas.py

install: $(VENV)/bin/activate $(H2C) ## Create .venv, install dependencies, fetch html2canvas

run: install ## Start the dev server on :$(PORT) with auto-reload
	RELOAD=1 PORT=$(PORT) $(PY) -m backend.server

test: install ## Run the unit tests
	$(PIP) install -q -r requirements-dev.txt
	$(PY) -m pytest -q tests

docker-build: ## Build the container image
	docker build -t $(IMAGE) .

docker-run: docker-build ## Run the container locally with your .env
	docker run --rm -it -p $(PORT):8080 --env-file $(ENV_FILE) \
		-v $(HOME)/.config/gcloud:/root/.config/gcloud:ro $(IMAGE)

deploy: ## Deploy to Cloud Run (see deploy.sh)
	./deploy.sh

demo-docs: ## Render the demo grounding docs (HTML) to PDF
	bash scripts/build_demo_docs.sh

provision: install ## Help for indexing a docs website in Agent Search
	$(PY) scripts/provision_engine.py --help

provision-docs: install ## Help for indexing PDFs in Agent Search
	$(PY) scripts/provision_docs.py --help

clean: ## Remove .venv and caches
	rm -rf $(VENV) .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
