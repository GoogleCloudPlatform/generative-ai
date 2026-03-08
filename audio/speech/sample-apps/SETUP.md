# Environment Setup for Audio/Speech Sample Apps

This guide walks you through setting up your Google Cloud environment to run the audio/speech sample applications.

## Prerequisites

1. Sign-in to the [Google Cloud Console](http://console.cloud.google.com/) and create a new project or reuse an existing one.

2. [Enable billing](https://console.cloud.google.com/billing) in the Cloud Console to use Cloud resources/APIs.

3. New Google Cloud users are eligible for the [$300 USD Free Trial](http://cloud.google.com/free) program.

## Start Cloud Shell

From the [Google Cloud Console](https://console.cloud.google.com/), click the Cloud Shell icon on the top right toolbar.

## Enable APIs

Enable the required APIs for your project:

```bash
gcloud services enable speech.googleapis.com
gcloud services enable texttospeech.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

## Set Environment Variables

```bash
export GOOGLE_CLOUD_PROJECT='<Your Google Cloud Project ID>'
export GOOGLE_CLOUD_REGION='us-central1'
```

## Authentication

Authenticate to your Google Cloud Project:

```bash
gcloud config set project $GOOGLE_CLOUD_PROJECT
gcloud auth application-default set-quota-project $GOOGLE_CLOUD_PROJECT
gcloud auth application-default login -q
```

## Next Steps

Once you have completed this setup, you can proceed to the individual sample app directories:

- [live-translator](./live-translator/) - Live translation demo with Streamlit

For more detailed setup instructions, see the main [gemini/sample-apps/SETUP.md](../../../gemini/sample-apps/SETUP.md).
