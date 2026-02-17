#!/bin/bash

# Copyright 2024 Google LLC
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     https://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Check if container name is provided
if [ $# -eq 0 ]; then
  echo "Error: Container name is required"
  echo "Usage: $0 [--running|--stopped] <container_name>"
  echo "       If flag is omitted, --running is assumed"
  exit 2
fi

# Set default values
FLAG="--running"
CONTAINER_NAME=$1

# Check if first argument is a flag
if [ "$1" == "--running" ] || [ "$1" == "--stopped" ]; then
  FLAG=$1
  
  # Check if container name is provided after the flag
  if [ $# -lt 2 ]; then
    echo "Error: Container name is required"
    echo "Usage: $0 [--running|--stopped] <container_name>"
    exit 2
  fi
  
  CONTAINER_NAME=$2
fi

# Check if the container is running
IS_RUNNING=0
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "Container ${CONTAINER_NAME} is running"
  IS_RUNNING=1
else
  echo "Container ${CONTAINER_NAME} is not running"
  IS_RUNNING=0
fi

# Determine exit code based on flag and container state
if [ "$FLAG" == "--running" ]; then
  # For --running flag, exit 0 if container is running, 1 otherwise
  if [ $IS_RUNNING -eq 1 ]; then
    exit 0
  else
    exit 1
  fi
else
  # For --stopped flag, exit 0 if container is not running, 1 otherwise
  if [ $IS_RUNNING -eq 0 ]; then
    exit 0
  else
    exit 1
  fi
fi
