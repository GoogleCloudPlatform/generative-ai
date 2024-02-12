#!/bin/bash

# This script allows you to authenticate BOTH through ADC and with normal gcloud login.
# These script require you to use both ADC (for text2speech) and gcloud login (for Gemini).
# If you find how to do with a single login, please write me or file a PR!
# This script also supports Service Account key. Just create a SA, give it the right powers,
# and then download the key. finally rename the key to "private/PROJECT_ID.json" to match
# the STD_SA_LOCATION var in this script.

set -euo pipefail

export CONFIG_NAME=${GCLOUD_CONFIG_NAME:-gemini-tests}

if [ -f .envrc ]; then
    source .envrc
fi

export STD_SA_LOCATION="private/$PROJECT_ID.json"

echo '💡 1. Setting up gcloud authentication..'

gcloud config configurations create "$CONFIG_NAME" --activate || \
	gcloud config configurations activate "$CONFIG_NAME"

gcloud config set project "$PROJECT_ID"
if [ -f "$STD_SA_LOCATION" ]; then
	echo "Standard SvcAcct key found: DHH would be so proud of me! Authenticating as SA"
	gcloud auth activate-service-account --key-file="$STD_SA_LOCATION"
# For TTS:
else
	echo "Standard SvcAcct key NOT found in $STD_SA_LOCATION: logging in as '$ACCOUNT' then."
	gcloud config set account "$ACCOUNT"
	gcloud auth login
fi


gcloud auth application-default set-quota-project "$PROJECT_ID"
gcloud auth application-default login

#	gcloud auth login
gcloud config set project "$PROJECT_ID"

# ENABLE APIs
#https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=rk-testing-gemini
echo '💡 2. Enabling APIs..'
gcloud services enable \
	cloudresourcemanager.googleapis.com \
	texttospeech.googleapis.com \
	aiplatform.googleapis.com

echo "💡 3. Now I will download images from GCS bucket:"
make images

echo "🟢 Done. You should be able to enjoy these scripts now! See README.md for some examples."
