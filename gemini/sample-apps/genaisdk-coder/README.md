# Streamlit App to write code using the Google Gen AI SDK

[![Run on Google Cloud](https://deploy.cloud.run/button.svg)](https://deploy.cloud.run)

| Authors                                        |
|------------------------------------------------|
| [Holt Skinner](https://github.com/holtskinner) |

This application demonstrates a Cloud Run application that uses the [Streamlit](https://streamlit.io/) framework.

## Run the Application locally (on Cloud Shell)

> NOTE: **Before you move forward, ensure that you have followed the instructions in [SETUP.md](../SETUP.md).**
> Additionally, ensure that you have cloned this repository and you are currently in the `gemini-streamlit-cloudrun` folder. This should be your active working directory for the rest of the commands.

To run the Streamlit Application locally (on Cloud Shell), we need to perform the following steps:

1. Setup the Python virtual environment and install the dependencies:

   In Cloud Shell, execute the following commands:

   ```bash
   python3 -m venv gemini-streamlit
   source gemini-streamlit/bin/activate
   pip install -r requirements.txt
   ```

2. Your application requires the following environment variables:

   - If you are using standard Vertex AI:

   ```bash
   export GOOGLE_CLOUD_PROJECT='<Your Google Cloud Project ID>'  # Change this
   export GOOGLE_CLOUD_REGION='us-central1' # If you change this, make sure the region is supported.
   ```

   - If you are using [Vertex AI in express mode](https://cloud.google.com/vertex-ai/generative-ai/docs/start/express-mode/overview):

   ```bash
   export GOOGLE_API_KEY='<Your Vertex AI API Key>'  # Change this
   ```

3. To run the application locally, execute the following command:

   In Cloud Shell, execute the following command:

   ```bash
   streamlit run app.py \
     --browser.serverAddress=localhost \
     --server.enableCORS=false \
     --server.enableXsrfProtection=false \
     --server.port 8080
   ```

The application will startup and you will be provided a URL to the application. Use Cloud Shell's [web preview](https://cloud.google.com/shell/docs/using-web-preview) function to launch the preview page. You may also visit that in the browser to view the application. Choose the functionality that you would like to check out and the application will prompt the Gemini API in Vertex AI and display the responses.

## Build and Deploy the Application to Cloud Run

> NOTE: **Before you move forward, ensure that you have followed the instructions in [SETUP.md](../SETUP.md).**
> Additionally, ensure that you have cloned this repository and you are currently in the `gemini-streamlit-cloudrun` folder. This should be your active working directory for the rest of the commands.

To deploy the Streamlit Application in [Cloud Run](https://cloud.google.com/run/docs/quickstarts/deploy-container), we need to perform the following steps:

1. Your Cloud Run app requires access to two environment variables:

   - `GOOGLE_CLOUD_PROJECT` : This the Google Cloud project ID.
   - `GOOGLE_CLOUD_REGION` : This is the region in which you are deploying your Cloud Run app. For e.g. us-central1.

   These variables are needed since Vertex AI needs the Google Cloud Project ID and the region.

   In Cloud Shell, execute the following commands:

   ```bash
   export GOOGLE_CLOUD_PROJECT='<Your Google Cloud Project ID>'  # Change this
   export GOOGLE_CLOUD_REGION='us-central1'                      # If you change this, make sure the region is supported.
   ```

2. Build and deploy the service to Cloud Run:

   In Cloud Shell, execute the following command to name the Cloud Run service:

   ```bash
   export SERVICE_NAME='gemini-streamlit-app' # This is the name of our Application and Cloud Run service. Change it if you'd like.
   ```

   In Cloud Shell, execute the following command:

   ```bash
   gcloud run deploy "$SERVICE_NAME" \
     --port=8080 \
     --source=. \
     --allow-unauthenticated \
     --region=$GOOGLE_CLOUD_REGION \
     --project=$GOOGLE_CLOUD_PROJECT \
     --set-env-vars=GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_REGION=$GOOGLE_CLOUD_REGION
   ```

On successful deployment, you will be provided a URL to the Cloud Run service. You can visit that in the browser to view the Cloud Run application that you just deployed. Choose the functionality that you would like to check out and the application will prompt the Gemini API in Vertex AI and display the responses.

Congratulations!
