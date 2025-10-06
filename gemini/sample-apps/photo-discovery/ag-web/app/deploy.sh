#!/bin/bash

# build an image 
gcr_image_path=gcr.io/<YOUR GOOGLE CLOUD PROJECT ID>/ag-web_$(date +%Y-%m-%d_%H-%M)
gcloud builds submit --tag $gcr_image_path

# deploy
gcloud run deploy ag-web --image $gcr_image_path --platform managed --region us-central1 --allow-unauthenticated --min-instances=1 --max-instances=1

