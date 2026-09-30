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

BINARY_NAME := gemini-agentic-video-go
BIN_DIR     := bin
TARGET      := $(BIN_DIR)/$(BINARY_NAME)

GO          := go
ADDLICENSE  := addlicense

.PHONY: all build clean run list compare multivideo multiturn test fmt vet license license-check help

all: build

## build: Compile the binary to ./bin
build:
	@mkdir -p $(BIN_DIR)
	$(GO) build -v -o $(TARGET) .

## clean: Remove build artifacts and temporary files
clean:
	rm -rf $(BIN_DIR)

## run: Run the application (default example 1, override with ARGS="...")
run: build
	@if [ -z "$(ARGS)" ]; then \
		./$(TARGET) example 1; \
	else \
		./$(TARGET) $(ARGS); \
	fi

## list: List all available tutorial scenarios in the catalog
list: build
	./$(TARGET) example list

## compare: Run the Agentic vs. Static performance comparison benchmark
compare: build
	./$(TARGET) compare $(ARGS)

## multivideo: Run multi-video comparative synthesis
multivideo: build
	./$(TARGET) multivideo $(ARGS)

## multiturn: Run multi-turn video dialogue demonstration
multiturn: build
	./$(TARGET) multiturn $(ARGS)

## test: Run tests
test:
	$(GO) test -v ./...

## fmt: Format Go code
fmt:
	$(GO) fmt ./...

## vet: Run go vet
vet:
	$(GO) vet ./...

## license: Apply Apache 2.0 license headers using addlicense
license:
	$(ADDLICENSE) -c "Google LLC" -y 2026 -l apache -v -ignore "sources/**" .

## license-check: Verify presence of license headers
license-check:
	$(ADDLICENSE) -check -ignore "sources/**" .

## help: Show this help message
help:
	@echo "Available make targets:"
	@sed -n 's/^##//p' $(MAKEFILE_LIST) | column -t -s ':' | sed -e 's/^/ /'
