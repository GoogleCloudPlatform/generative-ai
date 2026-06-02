#!/bin/bash
VENV_PATH="/usr/local/google/home/ntuteja/ge-migration-agent/.venv"
AGENTS_DIR="/usr/local/google/home/ntuteja/ge-migration-agent"

$VENV_PATH/bin/python $VENV_PATH/bin/adk web --port 8001 $AGENTS_DIR

