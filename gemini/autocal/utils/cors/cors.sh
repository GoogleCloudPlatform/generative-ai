#!/bin/sh

if [ -z "${BUCKET_NAME}" ]; then
  echo "Expected BUCKET_NAME environment variable to be set"
  exit 1
fi

gcloud storage buckets update "gs://${BUCKET_NAME}" --cors-file=cors.json
