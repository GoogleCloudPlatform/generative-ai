# Project Livewire - Google Cloud Run Deployment Guide

This guide provides step-by-step instructions for deploying the Project Livewire client and server components as containerized services on Google Cloud Run. This setup is recommended for a scalable and managed production-like environment.

## Prerequisites

1.  **Google Cloud Project:** You need an active Google Cloud project.
2.  **Google Cloud SDK (`gcloud`):** Installed and authenticated.
    *   [Install Guide](https://cloud.google.com/sdk/docs/install)
    *   Login: `gcloud auth login`
    *   Set your project: `gcloud config set project YOUR_PROJECT_ID` (Replace `YOUR_PROJECT_ID`)
3.  **Enabled APIs:** Ensure the following APIs are enabled in your project:
    *   Cloud Build API (`cloudbuild.googleapis.com`)
    *   Cloud Run API (`run.googleapis.com`)
    *   Secret Manager API (`secretmanager.googleapis.com`)
    *   IAM API (`iam.googleapis.com`)
    *   Container Registry API (`containerregistry.googleapis.com`) or Artifact Registry API (`artifactregistry.googleapis.com`)
    *   (Optional) Vertex AI API (`aiplatform.googleapis.com`) - If using the Vertex endpoint.
    *   (Optional) Cloud Functions API (`cloudfunctions.googleapis.com`) - For deploying tools.
    *   (Optional) Google Calendar API (`calendar-json.googleapis.com`) - For the calendar tool function.
    ```bash
    gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com iam.googleapis.com containerregistry.googleapis.com aiplatform.googleapis.com cloudfunctions.googleapis.com calendar-json.googleapis.com
    ```
4.  **Deployed Cloud Functions:** The backend server relies on Cloud Functions for tool integration (weather, calendar).
    *   Deploy these functions first by following the **[Cloud Functions Setup Guide](../cloud-functions/README.md)**.
    *   You do *not* need the function URLs in an `.env` file for Cloud Run deployment if you configure them via Secret Manager or pass them during backend deployment (though storing them in secrets is common).
5.  **Git Repository:** You should have the Project Livewire code cloned locally.

## Setup Steps

### 1. Create Backend Service Account

The Cloud Run service for the backend needs an identity to securely access other Google Cloud services like Secret Manager.

```bash
# Define service account name (optional, adjust if needed)
export BACKEND_SA_NAME="livewire-backend"
export PROJECT_ID=$(gcloud config get-value project)

# Create the service account
gcloud iam service-accounts create ${BACKEND_SA_NAME} \
    --description="Service account for Project Livewire backend Cloud Run service" \
    --display-name="Livewire Backend SA"

# Grant Secret Manager access to the service account
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${BACKEND_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# (Optional) Grant Vertex AI User role if using Vertex endpoint
# gcloud projects add-iam-policy-binding ${PROJECT_ID} \
#    --member="serviceAccount:${BACKEND_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
#    --role="roles/aiplatform.user"
```

### 2. Store Secrets in Secret Manager

Securely store API keys and potentially other sensitive configuration. The backend service account will access these.

*   **Google Gemini API Key:**
    ```bash
    # Replace YOUR_GEMINI_API_KEY with your actual key
    echo -n "YOUR_GEMINI_API_KEY" | \
      gcloud secrets create GOOGLE_API_KEY --replication-policy="automatic" --data-file=-
    ```
*   **OpenWeather API Key (for weather tool):**
    ```bash
    # Replace YOUR_OPENWEATHER_API_KEY with your actual key
    echo -n "YOUR_OPENWEATHER_API_KEY" | \
      gcloud secrets create OPENWEATHER_API_KEY --replication-policy="automatic" --data-file=-
    ```
*   **(Optional) Store Cloud Function URLs:** You can also store function URLs as secrets if preferred.
    ```bash
    # Example for Weather Function URL
    # echo -n "YOUR_WEATHER_FUNCTION_URL" | \
    #  gcloud secrets create WEATHER_FUNCTION_URL --replication-policy="automatic" --data-file=-
    ```
    *(Note: The current `server/config/config.py` primarily expects URLs from environment variables, but could be adapted to read them from secrets if desired).*

### 3. Deploy the Backend Server to Cloud Run

This uses Cloud Build (`server/cloudbuild.yaml`) to build the Docker image and deploy it to Cloud Run.

```bash
# Navigate to the project root directory
cd /path/to/project-livewire

# Submit the build and deployment job
# This uses the configuration in server/cloudbuild.yaml
# It sets PROJECT_ID and the service account during deployment
gcloud builds submit --config server/cloudbuild.yaml
```

*   **What `server/cloudbuild.yaml` does:**
    *   Builds a Docker image using `server/Dockerfile`.
    *   Pushes the image to Google Container Registry (or Artifact Registry).
    *   Deploys the image to Cloud Run as a service named `livewire-backend`.
    *   Sets the region (default `us-central1` - modify YAML if needed).
    *   Allows unauthenticated access (for easy client connection - **consider restricting access in production**).
    *   Sets the container port to `8081`.
    *   Sets environment variables (`PROJECT_ID`, `LOG_LEVEL`). You can add more here (like `VERTEX_API=true`, `VERTEX_LOCATION`, or Function URLs if not using secrets).
    *   Assigns the `livewire-backend` service account created earlier.

### 4. Get the Backend Service URL

After the deployment finishes, retrieve the URL of the backend service.

```bash
# Replace us-central1 if you deployed to a different region
export BACKEND_URL=$(gcloud run services describe livewire-backend --platform managed --region us-central1 --format 'value(status.url)')

# Verify the URL (should start with https://...)
echo "Backend URL: ${BACKEND_URL}"
```
**Important:** The client needs the **WebSocket** version of this URL (replace `https://` with `wss://`).

### 5. Deploy the Frontend Client to Cloud Run

This uses Cloud Build (`client/cloudbuild.yaml`) to build the client's Docker image (which uses nginx to serve static files) and deploy it. We pass the backend's WebSocket URL to the build process.

```bash
# Navigate to the project root directory (if not already there)
cd /path/to/project-livewire

# Construct the WebSocket URL for the backend
export WSS_BACKEND_URL=$(echo ${BACKEND_URL} | sed 's|https://|wss://|')
echo "WebSocket Backend URL: ${WSS_BACKEND_URL}"

# Submit the build and deployment job for the frontend
# Pass the WebSocket URL as a substitution variable
gcloud builds submit --config client/cloudbuild.yaml \
  --substitutions=_BACKEND_URL="${WSS_BACKEND_URL}"
```

*   **What `client/cloudbuild.yaml` does:**
    *   Builds a Docker image using `client/Dockerfile`.
    *   Pushes the image to Google Container Registry (or Artifact Registry).
    *   Deploys the image to Cloud Run as a service named `livewire-ui`.
    *   Sets the region (default `us-central1` - modify YAML if needed).
    *   Allows unauthenticated access.
    *   Sets the container port to `8080`.
    *   **Crucially:** It expects the `_BACKEND_URL` substitution. This URL is injected into the `nginx.conf` file *during the build process* so the client-side JavaScript can potentially fetch it or be configured accordingly. *(Self-correction: The current client JS hardcodes `ws://localhost:8081`. This needs adjustment for cloud deployment. A common pattern is to have the frontend fetch config from a `/config` endpoint served by nginx, which gets the URL via the build arg/env var, or embed it directly in the HTML/JS during build).*
    *   *Modification needed:* The client code (`client/src/api/gemini-api.js`) needs to be updated to dynamically use the backend URL provided during deployment, rather than hardcoding `ws://localhost:8081`. This could involve fetching a config file or having the build process replace a placeholder. The `cloudbuild.yaml` substitution provides the URL, but the client needs to *use* it. A simple approach for this setup might be to modify `client/cloudbuild.yaml` to directly replace the placeholder in `gemini-api.js` using `sed` before building the image.

### 6. Get the Frontend Service URL

Retrieve the URL for the deployed UI service.

```bash
# Replace us-central1 if you deployed to a different region
export FRONTEND_URL=$(gcloud run services describe livewire-ui --platform managed --region us-central1 --format 'value(status.url)')

# Print the URL
echo "Frontend URL: ${FRONTEND_URL}"
```

### 7. Access the Application

Open the `FRONTEND_URL` in your web browser to use the deployed Project Livewire application.

## Troubleshooting

*   **Cloud Build Failures:**
    *   Check the Cloud Build logs in the Google Cloud Console for detailed error messages.
    *   Ensure the Cloud Build service account has necessary permissions (e.g., to push to Container Registry, deploy to Cloud Run).
*   **Cloud Run Service Errors:**
    *   Check the "Logs" tab for your `livewire-backend` and `livewire-ui` services in the Cloud Run section of the Google Cloud Console.
    *   **Backend:** Look for errors related to Secret Manager access (check IAM roles), API key validity, connection issues to Gemini, or problems calling Cloud Functions. Ensure `PROJECT_ID` is correctly passed or available.
    *   **Frontend:** Look for nginx errors or issues serving files. Ensure the backend URL was correctly passed during the build and is accessible.
*   **Connection Issues (Client <-> Server):**
    *   Verify the WebSocket URL used by the client correctly points to the `wss://` version of the `livewire-backend` service URL.
    *   Ensure both Cloud Run services allow ingress traffic (e.g., `--allow-unauthenticated` was used, or appropriate authentication is configured if restricted). Check firewall rules if applicable.
*   **Secret Manager Access Denied:** Double-check that the `livewire-backend` service account has the `roles/secretmanager.secretAccessor` role assigned in IAM.
*   **Quota Errors:** Monitor API usage (Gemini, Cloud Functions, etc.) in the Google Cloud Console. You might be hitting free tier limits or project quotas.