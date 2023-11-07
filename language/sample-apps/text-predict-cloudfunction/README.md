# Cloud Function that wraps the PaLM Text Bison Models

This application demonstrates a Cloud Function written in Python that initializes the Vertex AI module and then provides an endpoint to invoke PaLM Text Bison model.

> NOTE: **Before you move forward, ensure that you have followed the instructions in [SETUP.md](../SETUP.md).**
Additionally, ensure that you have cloned this repository and are currently in the ```text-predict-cloudfunction``` folder for the rest of the commands.

## Environment variables required

Your Cloud Function requires access to two environment variables:

- `GCP_PROJECT` : This the Google Cloud Project Id.
- `GCP_REGION` : This is the region in which you are deploying your Cloud Function. For e.g. us-central1.

These variables are needed since the Vertex AI initialization needs the Google Cloud Project Id and the region. The specific code line from the `main.py` function is shown here:
`vertexai.init(project=PROJECT_ID, location=LOCATION)`

In Cloud Shell, execute the following commands:
```bash
export GCP_PROJECT='<Your GCP Project Id>'  # Change this
export GCP_REGION='us-central1'             # If you change this, make sure region is supported by Model Garden. When in doubt, keep this.
```

These variables can be set via the following [instructions](https://cloud.google.com/functions/docs/configuring/env-var) via any of the following ways:

1. At the time of [deploying](https://cloud.google.com/functions/docs/configuring/env-var#setting_runtime_environment_variables) the Google Cloud Function. We will be using this method in the next section when we deploy the Cloud Function.
2. [Updating](https://cloud.google.com/functions/docs/configuring/env-var#updating_runtime_environment_variables) the environment variables after deploying the Google Cloud Function.

## Deploying the Cloud Function

Assuming that you have a copy of this project on your local machine with `gcloud` SDK setup on the machine, follow these steps:

1. Go to the root folder of this project.
2. You should have both the `main.py` and `requirements.txt` file present in this folder.
3. Provide the following command:

   ```bash
   gcloud functions deploy predictText \
   --gen2 \
   --runtime=python311 \
   --region=$GCP_REGION \
   --source=. \
   --entry-point=predictText \
   --trigger-http \
   --set-env-vars=GCP_PROJECT=$GCP_PROJECT,GCP_REGION=$GCP_REGION \
   --allow-unauthenticated
   ```

## Invoking the Cloud Function

Since this Cloud Function is deployed with a HTTP trigger, you can directly invoke it. Sample calls are shown below:

```bash
curl -m 70 -X POST https://$GCP_REGION-$GCP_PROJECT.cloudfunctions.net/predictText \
-H "Content-Type: application/json" \
-d '{
  "prompt": "What are the best places to visit in the United States?"
}'
```
