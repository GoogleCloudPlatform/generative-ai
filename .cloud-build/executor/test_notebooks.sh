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

for x in $TARGET; do
  total_count=$((total_count + 1))
  # Use the full path from the repository for display name
  DISPLAY_NAME="${x##generative-ai/}"
  DISPLAY_NAME="${DISPLAY_NAME%.ipynb}-$current_date-$current_time"
  echo "Starting execution for ${x}"

  # Execute and get the operation ID
  OPERATION_ID=$(gcloud colab executions create \
    --display-name="$DISPLAY_NAME" \
    --notebook-runtime-template="$NOTEBOOK_RUNTIME_TEMPLATE" \
    --direct-content="$x" \
    --gcs-output-uri="$OUTPUT_URI" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --service-account="$SA" \
    --verbosity=debug \
    --execution-timeout="1h30m" \
    --format="value(name)")

  echo "Operation ID: $OPERATION_ID"
  TRUNCATED_OPERATION_ID=$(echo "$OPERATION_ID" | cut -c 67-85)

  # check job status
  echo "Waiting for execution to complete..."
  if ! EXECUTION_DETAILS=$(gcloud colab executions describe "$TRUNCATED_OPERATION_ID" --region="$REGION"); then
    echo "Error describing execution for ${x}. See logs for details."
    failed_count=$((failed_count + 1))
    failed_notebooks+=("${x}")
    continue
  else
    echo "Execution completed for ${x}"
  fi

  # Check the jobState
  JOB_STATE=$(echo "$EXECUTION_DETAILS" | grep "jobState:" | awk '{print $2}')
  if [[ "$JOB_STATE" == "JOB_STATE_SUCCEEDED" ]]; then
    echo "Notebook execution succeeded."
    successful_count=$((successful_count + 1))
    successful_notebooks+=("${x}")
  else
    echo "Notebook execution failed. Job state: $JOB_STATE. Please use id $TRUNCATED_OPERATION_ID to troubleshoot notebook ${x}. See log for details."
    failed_count=$((failed_count + 1))
    failed_notebooks+=("${x}")
    continue
  fi

done

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

# prep notebook name for pub/sub message
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
  #exit 1
fi

echo "All notebook executions completed."
