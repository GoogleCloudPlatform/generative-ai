#!/bin/bash

# Set -e to exit immediately if a command exits with a non-zero status.
set -e

# Function to handle signals (e.g., SIGTERM, SIGINT)
function handle_signal() {
  echo "Received signal. Stopping processes..."
  kill $core_pid $workflow_pid $interact_pid
  wait
  exit 0
}

# Trap signals to gracefully stop processes
trap handle_signal SIGTERM SIGINT

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

# # Wait for any process to exit OR a signal
# while wait -n; do 
#   # Check if a signal was received
#   if [ $? -gt 128 ]; then 
#     echo "Signal received. Exiting..."
#     exit 0 
#   fi
# done

# # Log the exit status of the process that exited first
# exit_status=$?
# echo "Process with PID $! exited with status $exit_status"

# # Exit with the exit status of the process that exited first
# exit $exit_status

# Wait for any process to exit OR a signal
while true; do
  # Wait for a child process to exit
  wait -n

  # Store the PID of the exited process
  exited_pid=$!

  # Check if a signal was received
  if [ $? -gt 128 ]; then
    echo "Signal received. Exiting..."
    exit 0
  fi

  # Check the exit status of the exited process
  if wait $exited_pid; then
    echo "Process $exited_pid exited successfully."
  else
    echo "Process $exited_pid failed with exit code $?"
    exit 1  # Or handle the error appropriately
  fi
done
