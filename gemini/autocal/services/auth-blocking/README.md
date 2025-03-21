# Authz Blocking Functions

## Overview

Implementation of an [Identity Platform Blocking Function](https://firebase.google.com/docs/auth/extend-with-blocking-functions?gen=2nd) that checks an allow-list for permitted emails.

### Allow List

The file [src/allow-list.ts](src/allow-list.ts) configures the allow list.

## Deploying

This requires two service accounts - one to build and one to run.

Terraform deploys this function for you. If you would like to re-deploy manually, run these commands:

```sh
export PROJECT_ID=PROJECT_ID
export LOCATION=europe-west1

gcloud functions deploy auth-blocking-before-signin \
  --gen2 \
  --runtime=nodejs22 \
  --region="${LOCATION}" \
  --source=. \
  --entry-point=beforeSignIn \
  --project="${PROJECT_ID}" \
  --build-service-account="projects/${PROJECT_ID}/serviceAccounts/auth-blocking-build@${PROJECT_ID}.iam.gserviceaccount.com" \
  --service-account="auth-blocking-function@${PROJECT_ID}.iam.gserviceaccount.com" \
  --trigger-http &

gcloud functions deploy auth-blocking-before-create \
  --gen2 \
  --runtime=nodejs22 \
  --region="${LOCATION}" \
  --source=. \
  --entry-point=beforeCreate \
  --project="${PROJECT_ID}" \
  --build-service-account="projects/${PROJECT_ID}/serviceAccounts/auth-blocking-build@${PROJECT_ID}.iam.gserviceaccount.com" \
  --service-account="auth-blocking-function@${PROJECT_ID}.iam.gserviceaccount.com" \
  --trigger-http
```
