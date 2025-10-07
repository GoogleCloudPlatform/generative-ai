#!/bin/bash

ISSUE_TITLE="Failed automated Notebook Testing"
ISSUE_LABELS="bug"
# ISSUE_ASSIGNEES="CadillacBurgess1"
REPO_OWNER="GoogleCloudPlatform"
REPO_NAME="generative-ai"
FAILURE_FILE="/workspace/Failure.txt"

if [ -f "$FAILURE_FILE" ]; then
  ISSUE_BODY=$(cat "$FAILURE_FILE")

  if ! gh issue create \
    -t "$ISSUE_TITLE" \
    -b "$ISSUE_BODY" \
    -l "$ISSUE_LABELS" \
    -a "$ISSUE_ASSIGNEES" \
    -R "$REPO_OWNER/$REPO_NAME"; then
    echo "Error creating issue."
    exit 1
  fi

  echo "Issue created with output of failed notebooks."
else
  echo "No notebooks failed. Issue creation skipped."
fi
