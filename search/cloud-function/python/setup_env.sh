#!/bin/bash
cp .env.example .env
PROJECT_ID=$(gcloud config get-value project)
sed -i.bak "s/PROJECT_ID=.*/PROJECT_ID=$PROJECT_ID/" .env && rm .env.bak
echo "Project ID set to $PROJECT_ID in .env file"
echo "Please open .env and set the LOCATION, DATA_STORE_ID, and enum values"
