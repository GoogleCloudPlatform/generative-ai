#!/bin/bash

# Set -e to exit immediately if a command exits with a non-zero status.
set -e

# Start core.py in the background and log its PID
echo "Starting core.py..."
python3 core.py &
core_pid=$!
echo "core.py started with PID: $core_pid"

# Wait for 15 seconds
echo "Waiting for 15 seconds..."
sleep 15

# Start workflow.py in the background and log its PID
echo "Starting workflow.py..."
python3 workflow.py &
workflow_pid=$!
echo "workflow.py started with PID: $workflow_pid"

# Wait for 15 seconds
echo "Waiting for 15 seconds..."
sleep 15

# Start interact.py in the foreground and log its PID
echo "Starting interact.py..."
python3 interact.py &
interact_pid=$!
echo "interact.py started with PID: $interact_pid"
