#!/usr/bin/env bash
#
# Cloud Run Deployer Script for livekit-adk

set -euo pipefail

# Colors for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}      Google Cloud Run Deployment Helper         ${NC}"
echo -e "${BLUE}==================================================${NC}"

# 1. Check dependencies
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed.${NC}"
    echo -e "Please install Google Cloud SDK first: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# 2. Determine GCP Project ID
ACTIVE_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
read -p "Enter Google Cloud Project ID [default: ${ACTIVE_PROJECT}]: " GCP_PROJECT
GCP_PROJECT=${GCP_PROJECT:-$ACTIVE_PROJECT}

if [ -z "$GCP_PROJECT" ]; then
    echo -e "${RED}Error: Google Cloud Project ID is required.${NC}"
    exit 1
fi

# Set current project
gcloud config set project "$GCP_PROJECT"

# 3. Configuration Prompting
read -p "Enter deployment region [default: us-central1]: " GCP_REGION
GCP_REGION=${GCP_REGION:-us-central1}

read -p "Enter Cloud Run service name [default: livekit-adk]: " SERVICE_NAME
SERVICE_NAME=${SERVICE_NAME:-livekit-adk}

REPO_NAME="livekit-adk-repo"
IMAGE_TAG="latest"
IMAGE_URI="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${REPO_NAME}/${SERVICE_NAME}:${IMAGE_TAG}"

echo -e "\n${YELLOW}Deployment Configuration Summary:${NC}"
echo -e "- GCP Project: ${GREEN}${GCP_PROJECT}${NC}"
echo -e "- Region:      ${GREEN}${GCP_REGION}${NC}"
echo -e "- Service:     ${GREEN}${SERVICE_NAME}${NC}"
echo -e "- Image URI:   ${GREEN}${IMAGE_URI}${NC}"
echo -e "--------------------------------------------------"

# 4. Enable Required GCP APIs
echo -e "${YELLOW}Enabling required Google Cloud APIs (Artifact Registry, Cloud Build, Cloud Run)...${NC}"
gcloud services enable \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    secretmanager.googleapis.com

# 5. Setup Artifact Registry Repo if missing
echo -e "${YELLOW}Checking Artifact Registry repository...${NC}"
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$GCP_REGION" &>/dev/null; then
    echo -e "Creating Artifact Registry repository '${REPO_NAME}' in '${GCP_REGION}'..."
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$GCP_REGION" \
        --description="Docker repository for livekit-adk voice applications"
else
    echo -e "${GREEN}Artifact Registry repository already exists.${NC}"
fi

# 6. Build and Push Image using Cloud Build
echo -e "${YELLOW}Compiling and uploading container using Google Cloud Build...${NC}"
gcloud builds submit --tag "$IMAGE_URI" .

# 7. Load and Prompt for environment variables from app/.env
echo -e "\n${YELLOW}Configuration & Environment Setup:${NC}"
echo -e "Loading default values from 'app/.env' if available..."

# Initialize variables with defaults
GOOGLE_GENAI_USE_VERTEXAI="TRUE"
GOOGLE_CLOUD_PROJECT="$GCP_PROJECT"
GOOGLE_CLOUD_LOCATION="us-central1"
DEMO_AGENT_MODEL="gemini-2.0-flash-exp"
LIVEKIT_URL=""
LIVEKIT_API_KEY=""
LIVEKIT_API_SECRET=""

ENV_FILE="app/.env"
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}Found existing environment configuration in ${ENV_FILE}.${NC}"
    # Extract values safely from the .env file
    GOOGLE_GENAI_USE_VERTEXAI=$(grep -E "^GOOGLE_GENAI_USE_VERTEXAI=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "TRUE")
    GOOGLE_CLOUD_PROJECT_ENV=$(grep -E "^GOOGLE_CLOUD_PROJECT=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "")
    GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT_ENV:-$GOOGLE_CLOUD_PROJECT}
    GOOGLE_CLOUD_LOCATION=$(grep -E "^GOOGLE_CLOUD_LOCATION=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "us-central1")
    DEMO_AGENT_MODEL=$(grep -E "^DEMO_AGENT_MODEL=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "gemini-2.0-flash-exp")
    LIVEKIT_URL=$(grep -E "^LIVEKIT_URL=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "")
    LIVEKIT_API_KEY=$(grep -E "^LIVEKIT_API_KEY=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "")
    LIVEKIT_API_SECRET=$(grep -E "^LIVEKIT_API_SECRET=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "")
fi

read -p "Enter GOOGLE_CLOUD_PROJECT [default: ${GOOGLE_CLOUD_PROJECT}]: " INPUT_PROJECT
GOOGLE_CLOUD_PROJECT=${INPUT_PROJECT:-$GOOGLE_CLOUD_PROJECT}

read -p "Enter GOOGLE_CLOUD_LOCATION [default: ${GOOGLE_CLOUD_LOCATION}]: " INPUT_LOCATION
GOOGLE_CLOUD_LOCATION=${INPUT_LOCATION:-$GOOGLE_CLOUD_LOCATION}

read -p "Enter DEMO_AGENT_MODEL [default: ${DEMO_AGENT_MODEL}]: " INPUT_MODEL
DEMO_AGENT_MODEL=${INPUT_MODEL:-$DEMO_AGENT_MODEL}

read -p "Enter LIVEKIT_URL [e.g. ws://<ip>:7880] [default: ${LIVEKIT_URL}]: " INPUT_LK_URL
LIVEKIT_URL=${INPUT_LK_URL:-$LIVEKIT_URL}

read -p "Enter LIVEKIT_API_KEY [default: ${LIVEKIT_API_KEY}]: " INPUT_LK_KEY
LIVEKIT_API_KEY=${INPUT_LK_KEY:-$LIVEKIT_API_KEY}

read -p "Enter LIVEKIT_API_SECRET [default: ${LIVEKIT_API_SECRET}]: " INPUT_LK_SECRET
LIVEKIT_API_SECRET=${INPUT_LK_SECRET:-$LIVEKIT_API_SECRET}

ENV_VARS="GOOGLE_GENAI_USE_VERTEXAI=${GOOGLE_GENAI_USE_VERTEXAI},GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION},DEMO_AGENT_MODEL=${DEMO_AGENT_MODEL},LIVEKIT_URL=${LIVEKIT_URL},LIVEKIT_API_KEY=${LIVEKIT_API_KEY},LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}"

# 8. Deploy to Cloud Run
echo -e "${YELLOW}Deploying container image to Google Cloud Run...${NC}"
gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_URI" \
    --region "$GCP_REGION" \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars "$ENV_VARS"

echo -e "\n${GREEN}==================================================${NC}"
echo -e "${GREEN}   Deployment Completed Successfully!             ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "You can monitor service logs in the Google Cloud Console."
