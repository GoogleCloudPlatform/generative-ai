#!/bin/bash
SCRIPT_DIR=$(dirname "$0")
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

uv run adk web --port 8001 "$PROJECT_ROOT"
