#!/usr/bin/env bash

# Enable Vertex AI
gcloud services enable aiplatform.googleapis.com

# Install frontend dependencies
cd frontend/
npm install
yarn install

# Build frontend
yarn build

# Install backend dependencies
cd ../
pip install -r requirements.txt

# Prompt the user for their API key
read -p "Enter your API Key: " API_KEY

# Save the API key to APIKey.txt
echo "$API_KEY" > APIKey.txt

# Optional: Display a success message
echo "API Key saved to APIKey.txt"

# Run backend
python main.py