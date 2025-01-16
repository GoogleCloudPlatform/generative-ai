# GenAI MLOps Tune and Evaluation
This tutorial will take you through using Vertex AI Pipelines to automate tuning an LLM and evaluating it against a previously tuned LLM. The example used is an LLM that summarizes a week of glucose values for a diabetes patient.

![Diagram](./diagram.png)

## Optional: Prepare the data
This step is optional because I've already prepared the data in `patient_1_glucose_examples.jsonl`.
* Create a week of glucose sample data for one patient using the following prompt with Gemini:
  ```
  Create a CSV with a week's worth of example glucose values for a diabetic patient. The columns should be date, time, patient ID, and glucose value.  Each day there should be timestamps for 7am, 8am, 11am, 12pm, 5pm, and 6pm. Most of the glucose values should be between 70 and 100. Some of the glucose values should be 100-150.
  ```
* Flatten the CSV by doing the following:
  1. Open the CSV
  2. Press Ctrl + a to select all text
  3. Press Alt + Shift + i to go to the end of each line
  4. Add a newline character (i.e. \n)
  5. Press Delete to squash it all to a single line
* Copy glucose_examples_template.jsonl to patient_X_glucose_examples.jsonl
* Copy the flattened CSV and paste it into the patient_X_glucose_examples.jsonl
* Flatten the contents of the patient_X_glucose_examples.jsonl file using a JSON to JSONL converter online

## Setup IAM, Tuning Examples, and Vertex AI Pipelines
* Grant default compute svc acct IAM permissions
  ```
  PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")
  SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

  gcloud projects add-iam-policy-binding $PROJECT_NUMBER \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/aiplatform.user"
  gcloud projects add-iam-policy-binding $PROJECT_NUMBER \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.objectUser"
  ```
* Create a GCS bucket and upload the JSONL with the glucose and analysis examples to tune the model:
  ```
  gsutil mb gs://glucose-test-bucket-$(date +%Y%m%d)
  gsutil cp patient_1_glucose_examples.jsonl gs://glucose-test-bucket-<DATETIME>
  ```
* Create the pipeline root bucket
  ```
  gsutil mb gs://vertex-ai-pipeline-root-$(date +%Y%m%d)
  ```

## Run Vertex AI Pipelines
* Install required packages and compile the pipeline
  ```
  python3 -m venv venv
  source venv/bin/activate
  pip install kfp google-cloud-aiplatform
  kfp dsl compile --py pipeline.py --output pipeline.json
  ```
* Edit `pipeline.py` and change the following:
  * `project` - change to your project ID
  * `train_data_uri` - change to `gs://glucose-test-bucket-<DATETIME>/patient_1_glucose_examples.jsonl`
* Edit `submit_pipeline_job.py` and change the following:
  * `pipeline_root` - change to the `gs://vertex-ai-pipeline-root-<DATETIME>` bucket you created earlier
  * `project` - change to your project ID
  * `train_data_uri` - change to `gs://glucose-test-bucket-<DATETIME>/patient_1_glucose_examples.jsonl`
* Create the pipeline run
  ```
  python submit_pipeline_job.py
  ```
* For subsequent runs, change `baseline_model_endpoint` in pipeline.py to a tuned model endpoint you want to compare against (typically the previously trained endpoint)

## Optional: Run Locally Using Kubeflow Pipelines
This step is optional because you can run the pipeline in Vertex AI Pipelines. However, if you're going to take this pipeline and develop on top of it, it's easier and faster to run the pipeline locally using Kubeflow.
* Install required packages
  ```
  cd ./local
  python3 -m venv venv
  source venv/bin/activate
  pip install kfp google-cloud-aiplatform vertexai plotly google-cloud-aiplatform[evaluation]
  ```
* Create local docker image using podman or docker-cli that has gcloud ADC copied over (**IMPORTANT:** never push this container to a public repo)
    ```
    gcloud auth application-default login
    cp $HOME/.config/gcloud/application_default_credentials.json .
    podman build -t python-3.9-gcloud .
    rm application_default_credentials.json
    ```
* Edit `pipeline.py` and change the following:
  * `project` - change to your project ID
  * `train_data_uri` - change to `gs://glucose-test-bucket-<DATETIME>/patient_1_glucose_examples.jsonl`
* Create the pipeline run
  ```
  python pipeline.py
  ```
* For subsequent runs, change `baseline_model_endpoint` in pipeline.py to a tuned model endpoint you want to compare against (typically the previously trained endpoint)