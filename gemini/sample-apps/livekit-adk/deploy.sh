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

# 7. Prompt for API secrets / credentials
echo -e "\n${YELLOW}LiveKit & Google Gemini Key Configuration:${NC}"
echo -e "To operate, your deployed Cloud Run agent requires external keys."
echo -e "Please choose one of the options below:"
echo -e " 1) Pass variables directly (e.g. as plain text values in Cloud Run)"
echo -e " 2) Setup later (deploy with dummy environment variable placeholders)"
read -p "Select option (1/2) [default: 1]: " CONFIG_OPTION
CONFIG_OPTION=${CONFIG_OPTION:-1}

ENV_VARS=""
if [ "$CONFIG_OPTION" = "1" ]; then
    read -p "Enter GOOGLE_API_KEY: " GOOGLE_API_KEY
    read -p "Enter LIVEKIT_URL [e.g., wss://<host>]: " LK_URL
    read -p "Enter LIVEKIT_API_KEY: " LK_KEY
    read -p "Enter LIVEKIT_API_SECRET: " LK_SECRET

    ENV_VARS="GOOGLE_API_KEY=${GOOGLE_API_KEY},GEMINI_API_KEY=${GOOGLE_API_KEY},USE_LIVEKIT=true,LIVEKIT_URL=${LK_URL},LIVEKIT_API_KEY=${LK_KEY},LIVEKIT_API_SECRET=${LK_SECRET}"
else
    echo -e "${YELLOW}Deploying with dummy placeholders. You must update them in Cloud Run Console later.${NC}"
    ENV_VARS="GOOGLE_API_KEY=PLACEHOLDER,USE_LIVEKIT=true,LIVEKIT_URL=PLACEHOLDER,LIVEKIT_API_KEY=PLACEHOLDER,LIVEKIT_API_SECRET=PLACEHOLDER"
fi

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
