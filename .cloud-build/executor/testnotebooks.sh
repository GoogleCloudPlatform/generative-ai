#!/bin/bash

alias gcurl='curl -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json"'

TARGET=$(cat .cloud-build/Notebooks.txt)

current_date=$(date +%Y-%m-%d)
current_time=$(date +%H-%M-%S)

NOTEBOOK_RUNTIME_TEMPLATE=$(cat NOTEBOOK_RUNTIME_TEMPLATE)
OUTPUT_URI=$(cat OUTPUT_URI)
SA=$(cat SA)
PROJECT_ID=$(cat PROJECT_ID)
REGION=$(cat REGION)

failed_count=0
failed_notebooks=()

for x in $TARGET
do
  DISPLAY_NAME="${x##*/}-$current_date-$current_time"
  echo "Starting execution for ${x##*/}"

  # Execute and get the operation ID
  OPERATION_ID=$(gcloud colab executions create \
    --display-name=$DISPLAY_NAME \
    --notebook-runtime-template=$NOTEBOOK_RUNTIME_TEMPLATE \
    --gcs-notebook-uri="$OUTPUT_URI/generative-ai/gemini/getting-started/${x##*/}" \
    --gcs-output-uri=$OUTPUT_URI \
    --project=$PROJECT_ID \
    --region=$REGION \
    --service-account=$SA \
    --verbosity=debug \
    --execution-timeout="1h30m" \
    --format="value(name)")

  echo "Operation ID: $OPERATION_ID"
  TRUNCATED_OPERATION_ID=$(echo $OPERATION_ID | cut -c 67-85)

  # check job status
  echo "Waiting for execution to complete..."
  EXECUTION_DETAILS=$(gcloud colab executions describe $TRUNCATED_OPERATION_ID --region=$REGION)
  if [[ $? -ne 0 ]]; then
    echo "Error describing execution for ${x##*/}. See logs for details."
    failed_count=$((failed_count + 1))
    continue
  else
    echo "Execution completed for ${x##*/}"
  fi

  # Check the jobState
  JOB_STATE=$(echo "$EXECUTION_DETAILS" | grep "jobState:" | awk '{print $2}')
  if [[ "$JOB_STATE" == "JOB_STATE_SUCCEEDED" ]]; then
    echo "Notebook execution succeeded."
  else
    echo "Notebook execution failed. Job state: $JOB_STATE. Please use id $TRUNCATED_OPERATION_ID to troubleshoot notebook ${x##*/}. See log for details."
    failed_count=$((failed_count + 1))
    failed_notebooks+=("${x##*/}")  
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

echo "All notebook executions completed."