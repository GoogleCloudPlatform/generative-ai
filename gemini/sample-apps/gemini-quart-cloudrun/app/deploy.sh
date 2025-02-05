#!/bin/bash
#set -e

# To run the app with Vertex AI, use this script as is.
# To run the app with Gemini API key, comment out the following lines.
PROJECT_ID=$(gcloud config get-value project)
export PROJECT_ID
LOCATION=us-central1
export LOCATION

# To run the app with Gemini API key, uncomment this and specify your key.
# (See: https://aistudio.google.com/apikey)
#export GEMINI_API_KEY=<YOUR GEMINI API KEY>

# Quart debug mode (True or False)
QUART_DEBUG_MODE=False
export QUART_DEBUG_MODE

# build an image
gcr_image_path=gcr.io/$PROJECT_ID/gemini-quart-cloudrun
gcloud builds submit --tag $gcr_image_path

# deploy
gcloud run deploy gemini-quart-cloudrun \
  --image $gcr_image_path \
  --platform managed \
  --allow-unauthenticated \
  --project=$PROJECT_ID --region=$LOCATION \
  --set-env-vars=PROJECT_ID=$PROJECT_ID \
  --set-env-vars=LOCATION=$LOCATION \
  --set-env-vars=GEMINI_API_KEY=$GEMINI_API_KEY \
  --set-env-vars=QUART_DEBUG_MODE=$QUART_DEBUG_MODE
