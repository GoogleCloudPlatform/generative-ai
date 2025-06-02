# Notebook Testing

This script is designed to automate the uploading of Jupyter Notebook files (`.ipynb`) from a local directory to a Google Cloud Storage (GCS) bucket

## Purpose

The script simplifies the process of transferring multiple notebook files to GCS, making it easier to manage and deploy your notebooks in a cloud environment.

## Script Description

The script performs the following actions:

1. **Reads Output URI variable:**
   - It reads the destination GCS bucket URI from a variable named `OUTPUT_URI` injected from secret manager. This allows for easy configuration of the destination.
2. **Iterates Through Notebooks:**
   - It loops through all `.ipynb` files located in the `Notebooks.txt` file.
3. **Copies Notebooks to GCS:**
   - For each notebook file, it extracts the filename using `basename`.
   - It then uses the `gcloud storage cp` command to copy the notebook file to the specified GCS bucket, maintaining the directory structure.

## Prerequisites

Before running this script, ensure you have the following:

- **Google Cloud SDK (gcloud):** The Google Cloud SDK must be installed and configured with appropriate credentials. You should be authenticated to the Google Cloud project where you want to upload the notebooks.
- **GCS Bucket:** The destination GCS bucket must exist.
- **OUTPUT_URI:** A secret named `OUTPUT_URI` must be injected for this step in your pipeline. This variable should contain the full GCS URI of the destination bucket (e.g., `gs://your-bucket-name`).
- **Jupyter Notebooks:** The Jupyter Notebook files (`.ipynb`) should be located in the `/workspace/generative-ai/gemini/getting-started/` directory.

## How to Use

1. **Set Up `OUTPUT_URI`:**

   - Create a variable named `OUTPUT_URI` in the same directory as your script.
   - Add the full GCS URI of your destination bucket to this file. For example:

     ```none
     gs://your-bucket-name
     ```

2. **Place Notebooks:**

   - Ensure the names of the `.ipynb` files are located in the `Notebooks.txt` file.

3. **Add the script as a step in your pipeline:**

## Example

Assuming you have a GCS bucket named `my-notebooks-bucket` and a notebook file named `example.ipynb` in the specified directory:

1. Create `OUTPUT_URI` variable the content: `gs://my-notebooks-bucket`
2. Place `example.ipynb` in `/workspace/generative-ai/gemini/getting-started/`
3. Run the script.
4. The `example.ipynb` will be copied to `gs://my-notebooks-bucket/generative-ai/gemini/getting-started/example.ipynb`.

## Notes

- Ensure that the service account used by `gcloud` has the necessary permissions to write to the GCS bucket.
- The script assumes that the directory `/workspace/generative-ai/gemini/getting-started/` exists. If it doesn't, the script will not find any notebooks.
- This script will overwrite files with the same name in the GCS bucket.
- If you have a large number of notebooks, consider adding error handling and logging to the script.
