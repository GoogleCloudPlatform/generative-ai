# Mesop application using Vertex AI Gemini API on Cloud Run

|           |                                                |
| --------- | ---------------------------------------------- |
| Author(s) | [Hussain Chinoy](https://github.com/ghchinoy) |

This application demonstrates a [Mesop](https://github.com/google/mesop) UI framework application running on Cloud Run.

Sample screenshots and video demos of the application are shown below:

## Application screenshots

![image playground](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/mesop-cloudrun/imageplayground.png)

## Run the Application locally (on Cloud Shell)

> NOTE: **Before you move forward, ensure that you have followed the instructions in [SETUP.md](../SETUP.md).**
> Additionally, ensure that you have cloned this repository and you are currently in the `gemini-mesop-cloudrun` folder. This should be your active working directory for the rest of the commands.

To run the Mesop application locally (on Cloud Shell), we need to perform the following steps:

1. Setup the Python virtual environment and install the dependencies:

   In Cloud Shell, execute the following commands:

   ```bash
   python3 -m venv gemini-mesop
   . gemini-mesop/bin/activate
   pip install -r requirements.txt
   ```

2. Your application requires access to two environment variables:

   - `GOOGLE_CLOUD_PROJECT` : This the Google Cloud project ID.
   - `GOOGLE_CLOUD_REGION` : This is the region in which you are deploying your Cloud Run app. For e.g. us-central1.

   These variables are needed since the Vertex AI initialization needs the Google Cloud project ID and the region. The specific code line from the `main.py`
   function is shown here:
   `vertexai.init(project=PROJECT_ID, location=LOCATION)`

   In Cloud Shell, execute the following commands:

   ```bash
   export GOOGLE_CLOUD_PROJECT=$(gcloud config get project)  # this will populate your current project ID
   export GOOGLE_CLOUD_REGION='us-central1'             # If you change this, make sure the region is supported.
   ```

3. To run the application locally, execute the following command:

   In Cloud Shell, execute the following command:

   ```bash
   mesop --port 8080 main.py
   ```

The application will startup and you will be provided a URL to the application. Use Cloud Shell's [web preview](https://cloud.google.com/shell/docs/using-web-preview) function to launch the preview page. You may also visit that in the browser to view the application. Choose the functionality that you would like to check out and the application will prompt the Vertex AI Gemini API and display the responses.

## Build and Deploy the Application to Cloud Run

To deploy the Mesop Application in [Cloud Run](https://cloud.google.com/run/docs/quickstarts/deploy-container), we need to perform the following steps:

1. Your Cloud Run app requires access to two environment variables:

   - `GOOGLE_CLOUD_PROJECT` : This the Google Cloud project ID.
   - `GOOGLE_CLOUD_REGION` : This is the region in which you are deploying your Cloud Run app. For e.g. us-central1.

   These variables are needed since the Vertex AI initialization needs the Google Cloud project ID and the region. The specific code line from the `main.py`
   function is shown here:
   `vertexai.init(project=PROJECT_ID, location=LOCATION)`

   In Cloud Shell, execute the following commands:

   ```bash
   export GOOGLE_CLOUD_PROJECT=$(gcloud config get project)   # Use this or manually change this
   export GOOGLE_CLOUD_REGION='us-central1'  # If you change this, make sure the region is supported.
   ```

2. Build and deploy the service to Cloud Run:

   In Cloud Shell, execute the following command to name the Cloud Run service:

   ```bash
   export SERVICE_NAME='mesop-gemini' # this is the name of our Application and Cloud Run service. Change this if you'd like to.
   ```


   In Cloud Shell, execute the following command:

   ```bash
   gcloud run deploy $SERVICE_NAME \
      --source . \
      --port=8080 --allow-unauthenticated \
      --project=$GOOGLE_CLOUD_PROJECT --region=$GOOGLE_CLOUD_REGION \
      --set-env-vars=GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT \
      --set-env-vars=GOOGLE_CLOUD_REGION=$GOOGLE_CLOUD_REGION
   ```

On successful deployment, you will be provided a URL to the Cloud Run service. You can visit that in the browser to view the Cloud Run application that you just deployed. Choose the functionality that you would like to check out and the application will prompt the Vertex AI Gemini API and display the responses.

Congratulations!
