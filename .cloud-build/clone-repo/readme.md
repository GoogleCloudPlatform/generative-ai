# Script for Copying Gemini Getting Started Files to GCS

This script automates the process of cloning your notebook repository and copys the notebook files to a specified Google Cloud Storage (GCS) location.

## Prerequisites

- **Google Cloud SDK (gcloud) installed and configured:** You need to have the `gcloud` command-line tool installed and authenticated with your Google Cloud account.
- **gsutil installed:** `gsutil` is part of the Google Cloud SDK and is used for interacting with GCS.
- **Git installed:** Git is required to clone the repository.
- **OUTPUT_URI:** A secret inject from secret manager in your GCP account

## How to use

1.  **Create `OUTPUT_URI` secret:**
    ```

    ```
2.  **Run the script:**
    Add script to pipeline

## Script Breakdown

```bash
#!/bin/bash

# Reads the destination GCS URI from the OUTPUT_URI file.
OUTPUT_URI=$(cat OUTPUT_URI)

# Clones the generative-ai repository from GitHub.
git clone [https://github.com/GoogleCloudPlatform/generative-ai.git](https://github.com/GoogleCloudPlatform/generative-ai.git)

# Changes the current directory to the cloned repository.
cd generative-ai

# Copies the specified directory to the destination GCS URI using gsutil.
gsutil -m cp -r . $OUTPUT_URI/generative-ai/gemini/getting-started/
```
