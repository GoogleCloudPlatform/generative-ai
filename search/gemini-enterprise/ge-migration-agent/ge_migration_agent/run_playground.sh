#!/bin/bash
VENV_PATH="/usr/local/google/home/ntuteja/ge-migration-agent/.venv"
AGENT_PATH="/usr/local/google/home/ntuteja/ge-migration-agent/notebook_agent"

$VENV_PATH/bin/python $VENV_PATH/bin/adk run $AGENT_PATH

