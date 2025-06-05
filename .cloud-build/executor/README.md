# Automated Vertex AI Colab Notebook Execution

This Bash script automates the execution of Jupyter Notebooks using Vertex AI Colab executions. It iterates through notebooks in a specified directory, triggers executions, and monitors their status.

## Purpose

The script aims to:

- Automate the execution of all `.ipynb` files located in `/workspace/generative-ai/gemini/getting-started`.
- Use a pre-configured Notebook Runtime Template.
- Store execution outputs in a Google Cloud Storage (GCS) bucket.
- Monitor execution status and identify failed notebooks.
- Output a list of failed notebooks to both the console and a file (`/workspace/Failure.txt`).

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and configured.
- Authentication set up with `gcloud auth login`.
- Vertex AI API enabled.
- Necessary variables (PROJECT_ID, REGION, SA, OUTPUT_URI, NOTEBOOK_RUNTIME_TEMPLATE) stored in separate secret manager in the same directory as the script.
- A Google Cloud Storage bucket accessible for storing notebook outputs.
- Notebook Runtime Template created in Google Cloud Vertex AI.
- Notebooks present in the `/workspace/generative-ai/gemini/getting-started` directory.

## Usage

1. **Prepare Variable in secret manager:** Create the following values in secret manager
   - `PROJECT_ID`: Your Google Cloud Project ID.
   - `REGION`: The Google Cloud region to use.
   - `SA`: The service account to use for the executions.
   - `OUTPUT_URI`: The GCS URI for storing execution outputs (e.g., `gs://your-bucket`).
   - `NOTEBOOK_RUNTIME_TEMPLATE`: The full resource name of your Notebook Runtime Template.
2. **Add to your pipeline:**
