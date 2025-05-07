#!/bin/bash

echo "Starting prepare_code.sh script..."

# https://github.com/google/adk-samples.git/adk-samples/agents/travel-concierge/travel_concierge # TODO: Pass this as a template parameter to generalize solution for any ADK agent
git clone https://github.com/google/adk-samples.git
cp -r adk-samples/agents/travel-concierge/travel_concierge ./travel_concierge
cp -r adk-samples/agents/travel-concierge/eval ./eval
cp adk-samples/agents/travel-concierge/pyproject.toml . # TODO: Installing dependencies might be necessary only for local and not AE deployment
cp adk-samples/agents/travel-concierge/poetry.lock .
poetry install --with deployment

echo "Finished prepare_code.sh script."