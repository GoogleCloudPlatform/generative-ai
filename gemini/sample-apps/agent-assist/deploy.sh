#!/bin/bash

npm run build --prefix frontend
cp -r frontend/build/ backend/src/build
gcloud run deploy agent-assist --source backend --port 8000 --region asia-south1 --platform managed --allow-unauthenticated