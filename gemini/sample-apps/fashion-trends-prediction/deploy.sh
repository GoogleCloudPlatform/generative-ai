#!/bin/bash
gcloud run deploy agent-assist --source backend --port 8501 --region asia-south1 --platform managed --allow-unauthenticated