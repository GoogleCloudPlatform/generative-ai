#!/bin/bash

ISSUE_TITLE="Failed automated Notebook Testing"
ISSUE_LABELS="bug"
ISSUE_ASSIGNEES="CadillacBurgess1"
REPO_OWNER="CadillacBurgess1"
REPO_NAME="example-notebook-testing-repo"
FAILURE_FILE="/workspace/Failure.txt"

if [ -f "$FAILURE_FILE" ]; then
  ISSUE_BODY=$(cat "$FAILURE_FILE")

  gh issue create \
    -t "$ISSUE_TITLE" \
    -b "$ISSUE_BODY" \
    -l "$ISSUE_LABELS" \
    -a "$ISSUE_ASSIGNEES" \
    -R "$REPO_OWNER/$REPO_NAME"

  if [ $? -ne 0 ]; then
    echo "Error creating issue."
    exit 1
  fi

  echo "Issue created with output of failed notebooks."
else
  echo "No notebooks failed. Issue creation skipped."
fi