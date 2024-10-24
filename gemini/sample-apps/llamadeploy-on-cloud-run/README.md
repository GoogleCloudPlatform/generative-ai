# Llama Deploy on Cloud Run

This repository contains a LlamaIndex Workflow application that demonstrates how to deploy and interact with Llama workflows using the `llama-deploy` library and deploying the service on Cloud Run.

The Workflow deployed on Cloud Run is a complex Retrieval Augmented Generation (RAG) workflow using Gemini models and Firestore databases.

## Authors

- Noa Ben-Efraim (`noabe`)

## Prerequisites

Before running this application on Cloud Run, make sure you have the following:

- **Google Cloud Project:** An active Google Cloud Project with billing enabled.
- **gcloud CLI:** The gcloud CLI installed and configured on your local machine. Authenticate to your Google Cloud project using `gcloud auth login`.
- **Docker:** Docker installed on your local machine to build and push the image.
- **Enabled APIs:** Enable the following APIs in your Google Cloud project:
  - Cloud Run API
  - Cloud Build API (if you want to build the image in Google Cloud)
  - Artifact Registry API (or Container Registry API)
- **Service Account:** A service account with the necessary permissions to access other Google Cloud resources used by your workflow (e.g., Firestore, Cloud Storage, Vertex AI). You can use the default Compute Engine service account or create a custom one.

### Download Data

We will be using The Great Gatsby text by F. Scott Fitzgerald for this example.

```bash
!mkdir data

!gcloud storage cp gs://github-repo/generative-ai/sample-apps/llamadeploy-on-cloud-run/gatsby.txt data
```

## Files

### 1. `core.py`

- **Purpose:** Launches the core services required for the Llama workflow application. This includes:
  - **Control Plane:** Manages workflow sessions and tasks.
  - **Message Queue:** Handles communication between services.
- **Usage:**
  - It uses the `llama-deploy` library to deploy the control plane and message queue.

### 2. `workflow.py`

- **Purpose:** Defines and deploys a Llama workflow.
- **Workflow Logic:**
  - Contains the `RAGWorkflow` class, which defines the steps in the workflow.
  - This workflow architects complex Retrieval Augmented Generation (RAG) workflow using Gemini models and Firestore databases.
  - The steps of the workflow are as follow:
    - Start Event triggered by providing a query to the workflow
    - The QueryMultiStep Event that breaks down a complex query into sequential sub-questions using Gemini. Then proceeds to answer the sub-questions.
    - The sub-questions results are passed to the RerankEvent where given the initial user query, Gemini reranks the returned answers to the sub-questions.
    - The reranked chunks are passed to the CreateCitationEvents where citations are added to the sub-questions used to generate the answer.
    - An answer is synthesized for the original query and returned to the user.
  - You can customize this class to implement your desired workflow logic.
  - For more information regarding `RAGWorkflow`, refer to this [notebook](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/orchestration/llamaindex_workflows.ipynb).
- **Usage:**
  - It uses the `llama-deploy` library to register the workflow with the control plane.

### 3. `interact.py`

- **Purpose:** Provides a Flask application to interact with the deployed workflow.
- **Functionality:**
  - Creates a Flask app with a POST endpoint (`/`) to receive workflow requests.
  - Handles incoming requests, extracts the workflow name and arguments, and runs the workflow using the `llama-deploy` client.
  - Returns the workflow result as a JSON response.
- **Usage:**
  - Send POST requests to the `/` endpoint with the workflow name and arguments to execute the workflow.

### 4. `Dockerfile`

- **Purpose:** Builds a Docker image for the Llama workflow application.
- **Instructions:**
  - Uses a Python base image.
  - Installs the required dependencies.
  - Copies the application code into the image.
  - Sets environment variables.
  - Creates a directory for data and copies the data into the image.
  - Makes the wrapper script executable.
  - Defines the command to run the application using the wrapper script.

### 5. `wrapper.sh`

- **Purpose:** A wrapper script to manage the application processes within the Docker container.
- **Functionality:**
  - Starts `core.py` and `workflow.py` in the background.
  - Waits for the services to start.
  - Runs `interact.py` in the foreground to keep the container running.
  - Handles signals (e.g., SIGTERM, SIGINT) to gracefully stop the processes.

## Running the Application

1. Create a repository that will be registered on Artifact Registry:

   ```bash
   gcloud artifacts repositories create my-docker-repo \
       --repository-format=docker \
       --location=us-west2 \
       --description="Docker repository for Llama workflow app"
   ```

2. Build the Docker image on Artifact Registry:

   ```bash
   gcloud builds submit —region=us-west2 —tag us-west2-docker.pkg.dev/[YOUR_PROJECT_ID]]/my-docker-repo/llama-workflows-app:first
   ```

3. Deploy the Docker Image to Cloud Run:

   ```bash
   gcloud run deploy llama-workflow-service \
   --image us-west2-docker.pkg.dev/[YOUR_PROJECT_ID]/my-docker-repo/llama-workflow-app:latest \
   --platform managed \
   --region us-west2 \
   --allow-unauthenticated \
   --set-env-vars PROJECT_ID="[YOUR_PROJECT_ID]",FIRESTORE_DATABASE_ID="[YOUR_FIRESTORE_DATABASE_ID]",LOCATION="[YOUR_PROJECT_LOCATION]
   ```

4. Interact with the service:

   ```bash
   curl \
   --header "Content-Type: application/json" \
   --request POST \
   --data '{"workflow": "my_workflow", "args": {"query": "your_query", "num_steps": 2}}' \
   <your-service-url>
   ```

## Contributing

Contributions to improve the system are welcome. Please follow the standard GitHub pull request process to submit your changes.

## License

This project is licensed under the standard Google Apache-2.0 license.

## Get in Touch

Please file any GitHub issues if you have any questions or suggestions.
