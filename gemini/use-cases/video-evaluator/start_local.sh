#!/bin/bash
# Copyright 2026 Google LLC
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


# Generative AI Video Evaluator Local Deployment Helper
echo "------------------------------------------------"
echo "🛡️ Generative AI Video Evaluator Local Deployment Starter"
echo "------------------------------------------------"

# Check for Docker
if ! [ -x "$(command -v docker)" ]; then
  echo "❌ Error: Docker is not installed. Please install Docker and try again."
  exit 1
fi

# Determine if using 'docker compose' or 'docker-compose'
DOCKER_CMD="docker compose"
if ! docker compose version > /dev/null 2>&1; then
  if [ -x "$(command -v docker-compose)" ]; then
    DOCKER_CMD="docker-compose"
  else
    echo "❌ Error: Neither 'docker compose' nor 'docker-compose' was found."
    exit 1
  fi
fi

# Build and start the container
echo "🏗️ Building and starting Generative AI Video Evaluator using $DOCKER_CMD..."
if $DOCKER_CMD up --build -d; then
  echo "------------------------------------------------"
  echo "✅ Generative AI Video Evaluator is running locally!"
  echo "📍 Access the dashboard at: http://localhost:3000"
  echo "⚙️ Configure your API key via the settings icon."
  echo "------------------------------------------------"
  echo "To stop the system, run: $DOCKER_CMD down"
  echo "To view logs, run: $DOCKER_CMD logs -f"
else
  echo "❌ Error: Failed to start the system. Check the output above for build errors."
  echo "💡 Tip: Try running '$DOCKER_CMD up --build' without '-d' to see full logs."
fi
