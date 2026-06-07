#!/bin/bash
SCRIPT_DIR=$(dirname "$0")
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
AGENT_PATH="$PROJECT_ROOT/notebook_agent"

uv run adk run "$AGENT_PATH"
