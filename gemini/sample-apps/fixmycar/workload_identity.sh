#!/bin/bash

# Create Kubernetes service account
kubectl create serviceaccount fixmycar

# Create GCP service account
gcloud iam service-accounts create fixmycar

# Grant GCP service account necessary IAM roles
# Note - providing all roles across both app flavors (Cloud SQL and Vertex AI Search)
GSA_MEMBER="fixmycar@${PROJECT_ID}.iam.gserviceaccount.com"

# IAM Role: Vertex AI Search (API is called DIscovery Engine)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member "serviceAccount:${GSA_MEMBER}" \
  --role "roles/discoveryengine.editor"

# IAM Role: Vertex AI Gemini API
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member "serviceAccount:${GSA_MEMBER}" \
  --role "roles/aiplatform.user"

# Create the two-way mapping between GSA <--> KSA
gcloud iam service-accounts add-iam-policy-binding $GSA_MEMBER \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:${PROJECT_ID}.svc.id.goog[default/fixmycar]"

kubectl annotate serviceaccount fixmycar \
  --namespace default \
  iam.gke.io/gcp-service-account=$GSA_MEMBER --overwrite

echo "✅ Workload Identity setup complete."
