# Cloud Function that demonstrates how to process an uploaded file in Google Cloud Storage and perform summarization using PaLM Vertex AI API on the contents

|           |                                              |
| --------- | -------------------------------------------- |
| Author(s) | [Romin Irani](https://github.com/rominirani) |

This application demonstrates a Cloud Function written in Python that gets triggered when a file is uploaded to a specific Google Cloud Storage bucket that is configured with. It does the following:

- Reads the content of the file.
- Invokes the PaLM Text Bison model with a Prompt to summarize the contents.
- Writes the summarized data into another Google Cloud Storage (GCS) bucket.

> NOTE: **Before you move forward, ensure that you have followed the instructions in [SETUP.md](../SETUP.md).**
> Additionally, ensure that you have cloned this repository and are currently in the `summarization-gcs-cloudfunction` folder. This should be your active working directory for the rest of the commands.

## Environment variables required

Your Cloud Function requires access to two environment variables:

- `GCP_PROJECT` : This the Google Cloud Project Id.
- `GCP_REGION` : This is the region in which you are deploying your Cloud Function. For e.g. us-central1.

These variables are needed since the Vertex AI initialization needs the Google Cloud Project Id and the region. The specific code line from the `main.py` function is shown here:
`vertexai.init(project=PROJECT_ID, location=LOCATION)`

In Cloud Shell, execute the following commands:

```bash
export GCP_PROJECT='<Your Google Cloud Project Id>'  # Change this
export GCP_REGION='us-central1'             # If you change this, make sure region is supported by Model Garden. When in doubt, keep this.
```

These variables can be set via the following [instructions](https://cloud.google.com/functions/docs/configuring/env-var) via any of the following ways:

1. At the time of [deploying](https://cloud.google.com/functions/docs/configuring/env-var#setting_runtime_environment_variables) the Google Cloud Function. We will be using this method in the next section when we deploy the Cloud Function.
2. [Updating](https://cloud.google.com/functions/docs/configuring/env-var#updating_runtime_environment_variables) the environment variables after deploying the Google Cloud Function.

## Deploying the Cloud Function and associated Cloud resources

### Create the GCS Buckets

We will need to create 2 GCS buckets:

- The first bucket will be used to upload the files to summarize. Let us call the bucket `$BUCKETNAME`. Create the environment variable to store your Bucket name as shown below:

```bash
export BUCKET_NAME='Your GCS Bucket Name'
```

- The second bucket will having a prefix `-summaries`.

You can create a bucket either from Google Cloud Console or from the command line via the `gsutil` command. Execute the commands below in Cloud Shell.

```bash
gsutil mb -l $GCP_REGION gs://"$BUCKET_NAME"
gsutil mb -l $GCP_REGION gs://"$BUCKET_NAME"-summaries
```

### Deploy the function

Assuming that you have a copy of this project on your local machine with `gcloud` SDK setup on the machine, follow these steps:

1. Go to the root folder of this project.
2. You should have both the `main.py` and `requirements.txt` file present in this folder.
3. Provide the following command:

   ```bash
   gcloud functions deploy summarizeArticles \
   --gen2 \
   --runtime=python311 \
   --source=. \
   --region=$GCP_REGION \
   --project=$GCP_PROJECT \
   --entry-point=summarize_gcs_object \
   --trigger-bucket=$BUCKET_NAME \
   --set-env-vars=GCP_PROJECT=$GCP_PROJECT,GCP_REGION=$GCP_REGION \
   --max-instances=1 \
   --quiet
   ```

## Invoking the Cloud Function

Since this Cloud Function is deployed with a GCS trigger, you will need to do the following to see the entire flow in action:

1. Ensure that you have the following GCS buckets created `$BUCKET_NAME` and `$BUCKET_NAME-summaries`.
2. Upload a file (a sample file [story.md](story.md) has been provided) with some text in the `$BUCKET_NAME` bucket.
3. This should trigger the `summarizeArticles` function and within a few seconds, you should see a `story.md` (summarized form) file created in the `$BUCKET-summaries` bucket.
