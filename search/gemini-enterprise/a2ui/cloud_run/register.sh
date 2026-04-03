#!/bin/bash
echo "Registering agent with Gemini Enterprise..."

if [ -f .env ]; then
    source .env
fi

# Use variables from .env or script arguments, with defaults for registration
SERVICE_URL=${SERVICE_URL:-$1}

if [[ -z "$SERVICE_URL" ]]; then
    echo "Usage: $0 [SERVICE_URL]"
    echo "Alternatively, set the SERVICE_URL environment variable."
    exit 1
fi

GEMINI_ENTERPRISE_APP_LOCATION=${GEMINI_ENTERPRISE_APP_LOCATION:-"global"}
ENGINE_ID=${GEMINI_ENTERPRISE_APP_ID:-"ENGINE_ID"}

# Fetch the agent card from the deployed service
echo "Fetching agent card from ${SERVICE_URL}/.well-known/agent-card.json..."
AGENT_CARD_JSON=$(curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" "${SERVICE_URL}/.well-known/agent-card.json")

if [[ -z "$AGENT_CARD_JSON" || "$AGENT_CARD_JSON" == "Unauthorized"* ]]; then
    echo "Error: Could not fetch agent card. Please ensure the service is accessible and gcloud is authenticated."
    exit 1
fi

# Extract agent details from the fetched JSON using jq
AGENT_NAME=$(echo "$AGENT_CARD_JSON" | jq -r '.name')
AGENT_DISPLAY_NAME=${AGENT_DISPLAY_NAME:-$(echo "$AGENT_CARD_JSON" | jq -r '.name')}
AGENT_DESCRIPTION=$(echo "$AGENT_CARD_JSON" | jq -r '.description')

# Escape the AGENT_CARD_JSON for use in the registration JSON payload
ESCAPED_AGENT_CARD_JSON=$(echo "$AGENT_CARD_JSON" | jq -c . | jq -R .)

curl -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/${GEMINI_ENTERPRISE_APP_LOCATION}/collections/default_collection/engines/${ENGINE_ID}/assistants/default_assistant/agents" \
  -d "{
  \"name\": \"${AGENT_NAME}\",
  \"displayName\": \"${AGENT_DISPLAY_NAME}\",
  \"description\": \"${AGENT_DESCRIPTION}\",
  \"a2aAgentDefinition\": {
     \"jsonAgentCard\": ${ESCAPED_AGENT_CARD_JSON}
  }
}"

echo -e "\nRegistration complete."
