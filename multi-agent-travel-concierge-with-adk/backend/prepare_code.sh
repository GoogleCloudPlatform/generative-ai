#!/bin/bash

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