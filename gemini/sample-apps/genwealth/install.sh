#!/usr/bin/env bash

###
### Deploys the genwealth app
###
### NOTE: you need the latest version of gcloud (i.e. 468 or later) to deploy this
###

# Function to handle incorrect usage
usage() {
  echo "Usage: $0 [--skip-org-policy-updates]"
  echo "Executes deploy-org-policies.sh, optionally skipping policy updates."
  exit 1
}

# Set the default behavior to update policies
skip_org_policies=false

# Process command-line flags
while [[ "$1" != "" ]]; do
  case "$1" in
  --skip-org-policy-updates) skip_org_policies=true ;;
  *) usage ;; # Catch any other flags as incorrect usage
  esac
  shift # Shift to the next argument
done

# Enable necessary APIs
echo "Enabling APIs."
source ./deployment/enable-apis.sh

# Deploy secrets
echo "Creating secrets."
source ./deployment/deploy-secrets.sh

# Update org policies unless skipped
if [[ $skip_org_policies == false ]]; then
  echo "Running organizational policy updates."
  echo "You can ignore org policy update errors if the erroring policy doesn't exist in your project."
  echo "You can skip org policy updates by running install.sh with the --skip-org-policy-updates flag."
  source ./deployment/deploy-org-policies.sh
else
  echo "Skipping organizational policy updates."
fi

# Deploy AlloyDB, pgAdmin, and database objects
echo "Deploying the back end."
source ./deployment/deploy-backend.sh

# Deploy the document ingestion pipeline
echo "Deploying the document ingestion pipeline."
source ./deployment/deploy-pipeline.sh

# Deploy Vertex AI Search
echo "Deploying Vertex AI Search."
source ./deployment/deploy-search.sh

# Deploy the registry
echo "Deploying front end dependencies."
source ./deployment/deploy-registry.sh

# Deploy the front end.
echo "Deploying the front end."
source ./deployment/deploy-frontend.sh

echo "Install complete."
