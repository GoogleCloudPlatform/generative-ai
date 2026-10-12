# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Gemini Live Studio: Go server + Lit frontend reference app for the Gemini
# Live API.

.PHONY: help dev run-backend run-frontend build container-build docker-build \
	lint license license-check test test-go test-frontend test-examples visual-check \
	deploy pack-skill

CONTAINER_CLI := $(shell if [ -x /usr/local/bin/container ]; then echo /usr/local/bin/container; else echo docker; fi)
IMAGE_TAG ?= gemini-live-studio:local
EXAMPLES := examples/local-code-assistant

LICENSE_IGNORES := -ignore '**/node_modules/**' -ignore '**/dist/**' \
	-ignore '**/*.json' -ignore '**/*.yaml' -ignore '**/*.yml' -ignore '**/*.md'

LINT_DEPS :=
DEPLOY_ENV :=
HELP_EXTRA :=

help:
	@echo "Gemini Live Studio - Makefile Commands"
	@echo "--------------------------------------"
	@echo "Local Development:"
	@echo "  make dev             - Start the Go server and the Vite dev server"
	@echo "  make run-backend     - Start only the Go server"
	@echo "  make run-frontend    - Start only the Vite dev server"
	@echo ""
	@echo "Quality & Build:"
	@echo "  make lint            - gofmt, go vet, golangci-lint + frontend eslint, tsc, prettier"
	@echo "  make test            - Go unit tests + frontend tests + examples"
	@echo "  make visual-check    - Screenshot + axe checks across views, themes, viewports"
	@echo "  make build           - Build the Go server and the frontend"
	@echo "  make container-build - Build the production container image"
	@echo "  make license-check   - Verify Apache-2.0 headers (needs addlicense)"
	@echo ""
	@echo "Deployment & Packaging:"
	@echo "  make deploy          - Deploy to Cloud Run (DEPLOY_ARGS=--dry-run to preview)"
	@echo "  make pack-skill      - Build the local-code-assistant agent skill bundle"
	@$(if $(HELP_EXTRA),echo; printf '%s\n' $(HELP_EXTRA))

dev:
	@$(MAKE) -j2 run-backend run-frontend

run-backend:
	@go run .

run-frontend:
	@cd frontend && npm run dev

build:
	@go build -o server .
	@cd frontend && npm run build

container-build:
	@echo "Building container image ($(IMAGE_TAG)) with $(CONTAINER_CLI)..."
	@$(CONTAINER_CLI) build -t $(IMAGE_TAG) .

docker-build: container-build

lint: $(LINT_DEPS)
	@unformatted="$$(gofmt -s -l $$(find . -name '*.go' -not -path '*/node_modules/*'))"; \
		test -z "$$unformatted" || { echo "gofmt -s needed:"; echo "$$unformatted"; exit 1; }
	@go vet .
	@for d in $(EXAMPLES); do (cd $$d && go vet ./...) || exit 1; done
	@if command -v golangci-lint >/dev/null; then \
		golangci-lint run . && for d in $(EXAMPLES); do (cd $$d && golangci-lint run ./...) || exit 1; done; \
	else echo "golangci-lint not installed; skipping (go install github.com/golangci/golangci-lint/v2/cmd/golangci-lint@latest)"; fi
	@cd frontend && npm run lint

test: test-go test-frontend test-examples

test-go:
	@go test .

# Frontend tests run in headless Chromium. First run:
# `cd frontend && npx playwright install chromium`, or set CHROMIUM_PATH.
test-frontend:
	@cd frontend && npm test && npm run manifest:check

test-examples:
	@for d in $(EXAMPLES); do (cd $$d && go test ./...) || exit 1; done

visual-check:
	@cd frontend && npm run visual

deploy:
	@$(DEPLOY_ENV) ./scripts/deploy.sh $(DEPLOY_ARGS)

# Every tracked code file carries the Apache-2.0 header.
# Install once: go install github.com/google/addlicense@latest
license-check:
	@addlicense -check -c "Google LLC" -l apache $(LICENSE_IGNORES) $$(git ls-files)

license:
	@addlicense -c "Google LLC" -l apache -y $$(date +%Y) $(LICENSE_IGNORES) $$(git ls-files)

# Portable agent skill: the skill files plus a copy of the example under assets/.
pack-skill:
	@rm -rf build/skill && mkdir -p build/skill/assets/local-code-assistant
	@cp -R examples/local-code-assistant/plugin/skills/local-code-assistant/. build/skill/
	@(cd examples/local-code-assistant && git ls-files -- . ':!plugin' | tar -cf - -T - | tar -xf - -C ../../build/skill/assets/local-code-assistant)
	@(cd build/skill && rm -f ../local-code-assistant.skill && \
		if command -v zip >/dev/null; then zip -qr ../local-code-assistant.skill . -x "*.DS_Store"; \
		else python3 -m zipfile -c ../local-code-assistant.skill $$(ls -A); fi)
	@echo "Wrote build/local-code-assistant.skill"
