#!/bin/bash

alias gcurl='curl -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json"'

TARGET=$(cat .cloud-build/Notebooks.txt)

current_date=$(date +%Y-%m-%d)
current_time=$(date +%H-%M-%S)
current_time_readable=$(date "+%B %d %Y %H:%M:%S")

NOTEBOOK_RUNTIME_TEMPLATE=$(cat NOTEBOOK_RUNTIME_TEMPLATE)
OUTPUT_URI=$(cat OUTPUT_URI)
SA=$(cat SA)
PROJECT_ID=$(cat PROJECT_ID)
REGION=$(cat REGION)
PUBSUB_TOPIC=$(cat PS_TOPIC)

failed_count=0
failed_notebooks=()
total_count=0
successful_notebooks=()
successful_count=0

# Array to store "OPERATION_ID:NOTEBOOK_PATH" for polling
launched_operation_details=()

echo "Starting to launch notebook executions..."

for x in $TARGET; do
  total_count=$((total_count + 1))
  # Use the full path from the repository for display name
  DISPLAY_NAME="${x##generative-ai/}"
  DISPLAY_NAME="${DISPLAY_NAME%.ipynb}-$current_date-$current_time"
  echo "Launching execution for ${x}"

  # Execute asynchronously and get the full operation name
  OPERATION_ID_FULL=$(gcloud colab executions create \
    --display-name="$DISPLAY_NAME" \
    --notebook-runtime-template="$NOTEBOOK_RUNTIME_TEMPLATE" \
    --direct-content="$x" \
    --gcs-output-uri="$OUTPUT_URI" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --service-account="$SA" \
    --verbosity=debug \
    --execution-timeout="1h30m" \
    --async \
    --format="value(name)")

  if [[ -z "$OPERATION_ID_FULL" ]]; then
    echo "Error: Failed to create execution for ${x}. No operation ID returned."
    failed_count=$((failed_count + 1))
    failed_notebooks+=("${x} (failed to launch)")
    continue
  fi

  # Extract the execution ID (last part of the full operation name)
  TRUNCATED_OPERATION_ID=$(basename "$OPERATION_ID_FULL")

  echo "Launched execution for ${x}, Operation ID: $TRUNCATED_OPERATION_ID (Full Name: $OPERATION_ID_FULL)"
  launched_operation_details+=("$TRUNCATED_OPERATION_ID:${x}")
done

echo "All notebook executions launched. Now waiting for completion..."

pending_operations=("${launched_operation_details[@]}")

while [[ ${#pending_operations[@]} -gt 0 ]]; do
  echo "Number of pending operations: ${#pending_operations[@]}"
  still_pending_next_round=() # Operations that are still PENDING/RUNNING for the next iteration

  for op_info in "${pending_operations[@]}"; do
    TRUNCATED_OPERATION_ID="${op_info%%:*}"
    NOTEBOOK_PATH="${op_info#*:}"

    echo "Checking status for operation: $TRUNCATED_OPERATION_ID (Notebook: $NOTEBOOK_PATH)"

    EXECUTION_DETAILS=""
    # Describe the execution. Added --project for explicitness.
    if ! EXECUTION_DETAILS=$(gcloud colab executions describe "$TRUNCATED_OPERATION_ID" --project="$PROJECT_ID" --region="$REGION" 2>&1); then
      echo "Error describing execution for $TRUNCATED_OPERATION_ID (Notebook: $NOTEBOOK_PATH). Marking as failed."
      echo "Describe error details: $EXECUTION_DETAILS"
      failed_count=$((failed_count + 1))
      failed_notebooks+=("${NOTEBOOK_PATH} (describe error)")
      continue # Handled (as failed), move to the next operation in this polling round
    fi

    # Parse the top-level 'state:' field from the describe output
    EXECUTION_STATE=$(echo "$EXECUTION_DETAILS" | grep -E "^state:" | awk '{print $2}')

    echo "Notebook: $NOTEBOOK_PATH, Operation: $TRUNCATED_OPERATION_ID, Execution State: $EXECUTION_STATE"

    if [[ "$EXECUTION_STATE" == "SUCCEEDED" ]]; then
      echo "Notebook execution succeeded for $NOTEBOOK_PATH."
      successful_count=$((successful_count + 1))
      successful_notebooks+=("${NOTEBOOK_PATH}")
    elif [[ "$EXECUTION_STATE" == "FAILED" || "$EXECUTION_STATE" == "CANCELLED" || "$EXECUTION_STATE" == "EXPIRED" ]]; then
      echo "Notebook execution failed, was cancelled, or expired for $NOTEBOOK_PATH. State: $EXECUTION_STATE. Please use id $TRUNCATED_OPERATION_ID to troubleshoot."
      failed_count=$((failed_count + 1))
      failed_notebooks+=("${NOTEBOOK_PATH}")
    elif [[ "$EXECUTION_STATE" == "PENDING" || "$EXECUTION_STATE" == "RUNNING" || "$EXECUTION_STATE" == "INITIALIZING" ]]; then
      echo "Notebook execution for $NOTEBOOK_PATH is still in progress (State: $EXECUTION_STATE). Will check again."
      still_pending_next_round+=("$op_info")
    else
      # Handle unknown or unexpected states
      echo "Unknown execution state '$EXECUTION_STATE' for $NOTEBOOK_PATH (Operation: $TRUNCATED_OPERATION_ID). Marking as failed."
      echo "Full describe output for unknown state: $EXECUTION_DETAILS"
      failed_count=$((failed_count + 1))
      failed_notebooks+=("${NOTEBOOK_PATH} (unknown state: $EXECUTION_STATE)")
    fi
  done

  pending_operations=("${still_pending_next_round[@]}")

  if [[ ${#pending_operations[@]} -gt 0 ]]; then
    SLEEP_DURATION=30 # seconds
    echo "Waiting for $SLEEP_DURATION seconds before next check for ${#pending_operations[@]} pending operations..."
    sleep $SLEEP_DURATION
  fi
done

echo "All executions have completed processing."

# Print the final list of failed notebooks
if [[ ${#failed_notebooks[@]} -gt 0 ]]; then
  echo "Failed Notebooks:"
  for notebook in "${failed_notebooks[@]}"; do
    echo "- $notebook" | tee -a /workspace/Failure.txt
  done
fi

if [[ $failed_count -gt 0 ]]; then
  echo "Total failed notebook executions: $failed_count"
fi

if [[ $successful_count -gt 0 ]]; then
  echo "Total successful notebook executions: $successful_count"
fi

# Prep pub/sub message
failed_notebooks_str=$(
  IFS=', '
  echo "${failed_notebooks[*]}"
)

if [[ -n "$failed_notebooks_str" ]]; then
  IFS=',' read -ra failed_notebooks_array <<<"$failed_notebooks_str"
  trimmed_notebooks=()
  for notebook in "${failed_notebooks_array[@]}"; do
    trimmed_notebooks+=("$(echo -n "$notebook" | sed 's/ *$//')")
  done
  failed_notebooks_str=$(
    IFS=', '
    echo "${trimmed_notebooks[*]}"
  )
else
  failed_notebooks_str=""
fi

successful_notebooks_str=$(
  IFS=', '
  echo "${successful_notebooks[*]}"
)

if [[ -n "$successful_notebooks_str" ]]; then
  IFS=',' read -ra successful_notebooks_array <<<"$successful_notebooks_str"
  trimmed_successful_notebooks=()
  for notebook in "${successful_notebooks_array[@]}"; do
    trimmed_successful_notebooks+=("$(echo -n "$notebook" | sed 's/ *$//')")
  done
  successful_notebooks_str=$(
    IFS=', '
    echo "${trimmed_successful_notebooks[*]}"
  )
else
  successful_notebooks_str=""
fi

# Construct the message to send to pub/sub topic
message_data="{\"total_count\":$((total_count + 0)),\"failed_count\":$((failed_count + 0)),\"failed_notebooks\":\"${failed_notebooks_str}\",\"successful_notebooks\":\"${successful_notebooks_str}\",\"successful_count\":$((successful_count + 0)),\"execution_date\":\"${current_time_readable}\"}"

# Publish to Pub/Sub
echo "$(date) - INFO - Publishing to Pub/Sub topic: $PUBSUB_TOPIC"
if ! gcloud pubsub topics publish "$PUBSUB_TOPIC" --message="$message_data" --project="$PROJECT_ID"; then
  echo "$(date) - ERROR - Failed to publish to Pub/Sub topic $PUBSUB_TOPIC. Check permissions and topic configuration."
fi

echo "All notebook test processing and reporting completed."
