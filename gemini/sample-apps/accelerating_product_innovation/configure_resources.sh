#!/bin/bash

file="env.txt"
previous_data=""

while IFS= read -r line; do
  echo "line: $line"
  for word in $line; do
    echo "pw: $previous_data, w: $word"
    case "$previous_data" in
      "PROJECT_ID")
        echo "pid"
        PROJECT_ID="$word"
        ;;
      "LOCATION")
        echo "loc"
        LOCATION="$word"
        ;;
      "REGION")
        echo "reg"
        REGION="$word"
        ;;
      "YOUR_EMAIL")
        echo "se"
        YOUR_EMAIL="$word"
        ;;
      "PROJECT_NUMBER")
        echo "pn"
        PROJECT_NUMBER="$word"
        ;;
    esac
    previous_data="$word"
  done
done <"$file"

echo "se: $YOUR_EMAIL"
echo "pn : $PROJECT_NUMBER"
echo "pID : $PROJECT_ID"

gcloud init --account "$YOUR_EMAIL" --project "$PROJECT_ID"
gcloud auth application-default set-quota-project "$PROJECT_ID"
gcloud config set project "$PROJECT_ID"

SERVICE_ACCOUNT="retail-accelerating-prod-i-982@$PROJECT_ID.iam.gserviceaccount.com"
gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT" --member "user:$YOUR_EMAIL" --role roles/iam.serviceAccountUser

gcloud functions deploy imagen-call \
  --allow-unauthenticated \
  --service-account="$SERVICE_ACCOUNT" \
  --run-service-account="$SERVICE_ACCOUNT" \
  --gen2 \
  --runtime=python311 \
  --region="$REGION" \
  --source=./cloud_functions/imagen_call \
  --entry-point=hello_http \
  --trigger-http \
  --set-env-vars location="$LOCATION" \
  --set-env-vars project_id="$PROJECT_ID" \
  --set-env-vars MEMORY=512MB >cloud_fn_1

file="cloud_fn_1"
previous_data=""
while IFS= read -r line; do
  for word in $line; do
    if [ "$previous_data" == "url:" ]; then
      imagen_call_url="$word"
    fi
    previous_data="$word"
  done
done <"$file"
echo "Imagen Call URL: $imagen_call_url" >cloud_functions_urls

gcloud functions deploy gemini-call \
  --allow-unauthenticated \
  --service-account="$SERVICE_ACCOUNT" \
  --run-service-account="$SERVICE_ACCOUNT" \
  --gen2 \
  --runtime=python311 \
  --region="$REGION" \
  --source=./cloud_functions/gemini-call \
  --entry-point=generate_text_http \
  --trigger-http \
  --set-env-vars location="$LOCATION" \
  --set-env-vars project_id="$PROJECT_ID" \
  --set-env-vars MEMORY=512MB >cloud_fn_1

while IFS= read -r line; do
  for word in $line; do
    if [ "$previous_data" == "url:" ]; then
      text_bison_url="$word"
    fi
    previous_data="$word"
  done
done <"$file"
echo "Text Bison Call URL: $text_bison_url" >>cloud_functions_urls

gcloud functions deploy text-embedding \
  --allow-unauthenticated \
  --service-account="$SERVICE_ACCOUNT" \
  --run-service-account="$SERVICE_ACCOUNT" \
  --gen2 \
  --runtime=python311 \
  --region="$REGION" \
  --source=./cloud_functions/text-embedding \
  --entry-point=hello_http \
  --trigger-http \
  --set-env-vars location="$LOCATION" \
  --set-env-vars project_id="$PROJECT_ID" \
  --set-env-vars MEMORY=512MB >cloud_fn_1

while IFS= read -r line; do
  for word in $line; do
    if [ "$previous_data" == "url:" ]; then
      text_embedding_url="$word"
    fi
    previous_data="$word"
  done
done <"$file"
echo "Text Embedding URL: $text_embedding_url" >>cloud_functions_urls
rm cloud_fn_1

# Set project ID, region, and service name (modify as needed)
SERVICE_NAME="accelerating-product-innovation"

# Build the container image (Cloud Buildpacks will detect Python)
gcloud builds submit --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME" .

# Deploy the image to Cloud Run
gcloud run deploy "$SERVICE_NAME" \
  --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
  --platform managed \
  --port 8080 \
  --region "$REGION" \
  --allow-unauthenticated
