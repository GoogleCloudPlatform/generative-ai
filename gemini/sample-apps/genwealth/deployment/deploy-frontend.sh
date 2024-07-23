#!/usr/bin/env bash

# Load env variables
source ./env.sh

if [ -z "$REGION" ]; then
  echo "REGION is not set. Please set the gcloud run/region."
  exit 1
fi

# Get the latest tags.
git fetch

# Update Vertex AI S&C configs
sed -i "s/genwealth-docs/${DOCS_BUCKET}/" ui/src/app/research/research.component.html
sed -i "s/8cb387aa-cc8b-4c1b-984a-0ea32285eebc/${SEARCH_CONFIG_ID}/" ui/src/app/research/research.component.html

#
# Build & push the container
#
echo "Building and pushing the container"
TAG_NAME=$(git describe --abbrev=0 --tags --always)
IMAGE=$REGION-docker.pkg.dev/$PROJECT_ID/genwealth/genwealth:$TAG_NAME

docker build --rm -t "$IMAGE" .
docker push "$IMAGE"

#
# Step 3: Deploy to Cloud Run
#
echo "Deploying to Cloud Run"
gcloud beta run deploy genwealth \
  --image="$IMAGE" \
  --execution-environment=gen2 \
  --cpu-boost \
  --network="$VPC_NETWORK" \
  --subnet="$VPC_SUBNET" \
  --vpc-egress=private-ranges-only \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --allow-unauthenticated \
  --set-env-vars=PGHOST="$PGHOST",PGPORT="$PGPORT",PGDATABASE="$PGDATABASE",PGUSER="$PGUSER",PGPASSWORD="$PGPASSWORD",DATASTORE_ID="$DATASTORE_ID",PROSPECTUS_BUCKET="$PROSPECTUS_BUCKET",PROJECT_ID="$PROJECT_ID",REGION="$REGION"
