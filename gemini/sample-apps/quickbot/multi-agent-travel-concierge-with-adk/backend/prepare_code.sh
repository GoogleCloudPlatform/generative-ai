#!/bin/bash
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


echo "Starting prepare_code.sh script..."

# TODO: Pass this as a template parameter to generalize solution for any ADK agent
# https://github.com/google/adk-samples.git/adk-samples/python/agents/travel-concierge/travel_concierge
git clone https://github.com/google/adk-samples.git
git checkout adf6402 # Go to a particular working commit as this changes quite regularly
cp -r adk-samples/python/agents/travel-concierge/travel_concierge ./travel_concierge
cp -r adk-samples/python/agents/travel-concierge/eval ./eval
cp adk-samples/python/agents/travel-concierge/pyproject.toml .
poetry install --with deployment

# Install setup.py dependencies
poetry add google-cloud-bigquery
poetry add google-cloud-logging
poetry add google-cloud-storage@2.19.0
poetry add requests

echo "Finished prepare_code.sh script."