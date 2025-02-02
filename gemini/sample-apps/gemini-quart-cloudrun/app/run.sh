#!/bin/bash
#set -e

# To run the app with Vertex AI, use this script as is.
# To run the app with Gemini API key, comment out these.
export PROJECT_ID=$(gcloud config get-value project)
export LOCATION=us-central1

# To run the app with Gemini API key, uncomment this and specify your key
# (See: https://aistudio.google.com/apikey)
#export GEMINI_API_KEY=<YOUR GEMINI API KEY>

# Quart debug mode (True or False)
export QUART_DEBUG_MODE=True

python3 app.py
