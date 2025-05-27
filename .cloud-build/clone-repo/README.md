# Script for Copying Gemini Getting Started Files to GCS

This script automates the process of cloning your notebook repository and will copy the notebook files to a specified Google Cloud Storage (GCS) location.

## Prerequisites

- **Google Cloud SDK (gcloud) installed and configured:** You need to have the `gcloud` command-line tool installed and authenticated with your Google Cloud account.
- **gsutil installed:** `gsutil` is part of the Google Cloud SDK and is used for interacting with GCS.
- **Git installed:** Git is required to clone the repository.
- **OUTPUT_URI:** A secret inject from secret manager Google Cloud in your account.

## How to use

1. **Create `OUTPUT_URI` secret:**

2. **Run the script:**
   Add script to pipeline
