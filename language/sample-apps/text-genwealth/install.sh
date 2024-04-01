###
### Deploys the genwealth app 
###
### NOTE: you need the latest version of gcloud (i.e. 468 or later) to deploy this
###

# Deploy each layer of the stack
echo "Deploying the back end."
source ./deployment/deploy-backend.sh
echo "Deploying the document ingestion pipeline."
source ./deployment/deploy-pipeline.sh
echo "Deploying Vertex AI Search and Conversation."
source ./deployment/deploy-search.sh
echo "Deploying front end dependencies."
source ./deployment/deploy-registry.sh
echo "Deploying the front end."
source ./deployment/deploy-frontend.sh
echo "Install complete."
