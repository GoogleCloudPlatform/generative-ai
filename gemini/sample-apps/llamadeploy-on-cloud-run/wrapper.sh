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
python3 interact.py 
interact_pid=$!
echo "interact.py started with PID: $interact_pid"

# Function to handle signals (e.g., SIGTERM, SIGINT)
function handle_signal() {
  echo "Received signal. Stopping processes..."
  kill $core_pid $workflow_pid $interact_pid
  wait
  exit 0
}

# Trap signals to gracefully stop processes
trap handle_signal SIGTERM SIGINT

# Wait for any process to exit
wait -n

# Log the exit status of the process that exited first
exit_status=$?
echo "Process with PID $! exited with status $exit_status"

# Exit with the exit status of the process that exited first
exit $exit_status
