
# Cloud Function for Document AI Processing with Gemini

This repository contains a Cloud Function that demonstrates a pipeline for processing documents using Google Cloud's Document AI and Gemini. The function is triggered when a new document is uploaded to a designated Cloud Storage bucket.

## Pipeline Overview

1. **Document Upload:** A user uploads a document to a specific Cloud Storage bucket.
2. **Event Trigger:** The upload event triggers a Cloud Pub/Sub notification.
3. **Cloud Function Activation:** The Cloud Function subscribes to the Pub/Sub topic and is activated upon receiving the notification.
4. **Document AI Processing:** The function utilizes the Document AI API to extract structured data from the uploaded document.
5. **Gemini Integration:** The extracted data is then processed or analyzed using Gemini, Google's large language model.

## Prerequisites

- **Google Cloud Project:** An active Google Cloud project with billing enabled.
- **Cloud Storage Buckets:** Three Cloud Storage buckets:
    - Input bucket for document uploads.
    - Temporary bucket for intermediate processing files.
    - Output bucket for storing processed results.
- **Cloud Pub/Sub Topic:** A Pub/Sub topic for receiving document upload notifications.
- **Document AI API:** Enable the Document AI API in your Google Cloud project.
- **Service Account:** A service account with the necessary permissions to access Cloud Storage, Pub/Sub, and Document AI.

## Deployment


1. **Clone the Repository:**
   ```bash
   git clone https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/use-cases/applying-llms-to-data/docai-gemini.git
   cd docai-gemini/cf-trigger-event/
   ```

2. **Set Environment Variables:**
   ```bash
   export PROJECT_ID=$(gcloud config get-value project)
   export REGION=us-central1
   export BUCKET_NAME="gs://$PROJECT_ID-documents"
   export TEMP_BUCKET="gs://$PROJECT_ID-documents-temp"
   export OUT_BUCKET="gs://$PROJECT_ID-documents-out"
   export TOPIC_NAME="documents"
   export PROCESSOR_ID=your-processor-id
   export PROCESSOR_VERSION_ID=your-processor-version
   ```
3. **Create Cloud Storage Buckets:**
   ```bash
   gsutil mb -p $PROJECT_ID $BUCKET_NAME
   gsutil mb -p $PROJECT_ID $TEMP_BUCKET
   gsutil mb -p $PROJECT_ID $OUT_BUCKET

   # Verify the bucket was created
   gsutil ls -p $PROJECT_ID
   ```
4. **Create Pub/Sub Topic:**
   ```bash   
    gcloud pubsub topics create $TOPIC_NAME    
   ```
5. **Configure Bucket Notifications:**
   ```bash
    gcloud storage buckets notifications create \
    --event-types=OBJECT_FINALIZE \
    --topic=$TOPIC_NAME $BUCKET_NAME 
   ```
6. **Deploy the Cloud Function:**
    ```bash
   gcloud functions deploy doc_ai_gemini_extractor \
   --project=$PROJECT_ID \
   --region=$REGION \
   --runtime python312 \
   --trigger-topic $TOPIC_NAME \
   --source . \
   --entry-point on_document_added \
   --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION,PROCESSOR_ID=$PROCESSOR_ID,PROCESSOR_VERSION_ID=$PROCESSOR_VERSION_ID,TEMP_BUCKET=$TEMP_BUCKET, OUTPUT_BUCKET=$OUT_BUCKET" \
   --timeout 240s \
   --memory 512MB \
   --gen2
    ```

# Usage
1. Upload a document to the designated input Cloud Storage bucket. 
2. The Cloud Function will be triggered automatically.

# Notes
- Ensure that the service account used by the Cloud Function has the necessary permissions to access the required Google Cloud services.
- Adjust the timeout and memory settings for the Cloud Function based on the complexity and size of the documents being processed.
- Refer to the Google Cloud documentation for detailed information on Document AI, Gemini, Cloud Functions, Cloud Storage, and Pub/Sub.