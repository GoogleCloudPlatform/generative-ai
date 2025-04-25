git clone https://github.com/google/adk-samples.git
cp -r adk-samples/agents/travel-concierge/travel_concierge ./travel_concierge
cp adk-samples/agents/travel-concierge/pyproject.toml .
cp adk-samples/agents/travel-concierge/poetry.lock .
poetry install --with deployment