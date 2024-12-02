# Agentic RAG with Vertex AI Search

This pattern enhances the Gen AI App Starter Pack with a production-ready data ingestion pipeline, enriching your Retrieval Augmented Generation (RAG) applications. Using Vertex AI Search's state-of-the-art search capabilities, you can ingest, process, and embed custom data, improving the relevance and context of your generated responses.

The pattern provides the infrastructure to create a Vertex AI Pipeline with your custom code. Because it's built on Vertex AI Pipelines, you benefit from features like scheduled runs, recurring executions, and on-demand triggers. For processing terabyte-scale data, we recommend combining Vertex AI Pipelines with data analytics tools like BigQuery or Dataflow.

![search pattern demo](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/starter-pack-search-pattern.gif)

## Architecture

The pattern implements the following architecture:

![architecture diagram](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/agentic_rag_vertex_ai_search_architecture.png)

### Key Features

- **Vertex AI Search Integration:** Utilizes Vertex AI Search for efficient data storage and retrieval.
- **Automated Data Ingestion Pipeline:** Automates the process of ingesting data from input sources.
- **Custom Embeddings:** Generates embeddings using Vertex AI Embeddings and incorporates them into your data for enhanced semantic search.
- **Terraform Deployment:** Ingestion pipeline is instantiated with Terraform alongside the rest of the infrastructure of the starter pack.
- **Cloud Build Integration:** Deployment of ingestion pipelines is added to the CD pipelines of the starter pack.
- **Customizable Code:** Easily adapt and customize the code to fit your specific application needs and data sources.

From an infrastructure point of view, a _Vertex AI Agent Builder Datastore_ and _Search App_ are being initialised in both staging and prod environments. You can learn more about these [here](https://cloud.google.com/generative-ai-app-builder/docs/enterprise-search-introduction).

When a new build is triggered through a commit to the main branch, in addition to updating the backend application, the data ingestion pipeline is also updated.

The data ingestion is orchestrated through a Vertex AI [Pipeline](https://cloud.google.com/vertex-ai/docs/pipelines/introduction) which in its simplest form comprises of a two processing step.
The pipeline reads data from a source (e.g., a PDF document) located at a configurable location. The data is then divided into smaller chunks, processed, and ingested into the Vertex AI Agent Builder Datastore. Upon ingestion completion, the connected Search App is automatically updated with the new data without any downtime.

Please note that the ingestion in the example is set to run automatically once per week. You may change the frequency of the update or the triggering mechanism altogether to match your needs. Look into the `data_processing/data_processing_pipeline/pipeline.py` and `deployment/cd/deploy-to-prod.yaml` files as the starting point for these changes.

## Getting Started

1. **Prepare the pattern:** First, prepare the pattern for data ingestion. In a clean instance of the starter pack, navigate to the `agentic_rag_vertex_ai_search` directory and execute the following command:

   ```bash
   python app/patterns/agentic_rag_vertex_ai_search/pattern_setup/prepare_pattern.py
   ```

2. **Setup Dev Terraform:** Follow the instructions in the parent [deployment/README.md - Dev Deployment section](../../../deployment/README.md#dev-deployment) to set up the development environment using Terraform. This will deploy a datastore and configure the necessary permissions in your development project.

   Refer to the [Terraform Variables section](#terraform-variables) to learn about the additional variables required for this pattern.

3. **Test the Data Ingestion Pipeline:**

   After successfully deploying the Terraform infrastructure, you can test the data ingestion pipeline. This pipeline is responsible for loading, chunking, embedding, and importing your data into the Vertex AI Search datastore.

   > Note: The first pipeline execution may take additional time as your project is being configured to use Vertex AI Pipelines.

   **a. Navigate to the Data Processing Directory:**

   Change your working directory to the location of the data processing scripts:

   ```bash
   cd data_processing
   ```

   **b. Install Dependencies:**

   Ensure you have the necessary Python dependencies installed by running:

   ```bash
   poetry install
   ```

   **c. Execute the Pipeline:**

   Use the following command to execute the data ingestion pipeline. Replace the placeholder values with your actual project details:

   ```bash
   PROJECT_ID="YOUR_PROJECT_ID"
   REGION="us-central1"
   REGION_VERTEX_AI_SEARCH="us"
   poetry run python data_processing_pipeline/submit_pipeline.py \
       --project-id=$PROJECT_ID \
       --region=$REGION \
       --region-vertex-ai-search=$REGION_VERTEX_AI_SEARCH \
       --data-store-id="sample-datastore" \
       --service-account="vertexai-pipelines-sa@$PROJECT_ID.iam.gserviceaccount.com" \
       --pipeline-root="gs://$PROJECT_ID-pipeline-artifacts" \
       --pipeline-name="data-ingestion-pipeline"
   ```

   **Explanation of Parameters:**

   - `--project-id`: Your Google Cloud Project ID.
   - `--region`: The region where Vertex AI Pipelines will be executed (e.g., `us-central1`).
   - `--region-vertex-ai-search`: The region for Vertex AI Search operations (e.g., `us` or `eu`).
   - `--data-store-id`: The ID of your Vertex AI Search data store.
   - `--service-account`: The service account email used for pipeline execution.
   - `--pipeline-root`: The GCS bucket name for storing pipeline artifacts.
   - `--pipeline-name`: A display name for your pipeline.
   - `--schedule-only`: _(Optional)_ If true, only schedules the pipeline without immediate execution. Must be used with `--cron-schedule`.
   - `--cron-schedule`: _(Optional)_ A cron schedule to run the pipeline periodically (e.g., `"0 9 * * 1"` for every Monday at 9 AM UTC).

   **d. Pipeline Execution Behavior:**

   The pipeline executes immediately. Use the `--schedule-only` flag with a `cron_schedule` to only schedule the pipeline without immediate execution. If no schedule exists, one is created. If a schedule exists, its cron expression is updated.

   **e. Monitoring Pipeline Execution:**

   The pipeline will output its configuration and execution status to the console. For detailed monitoring, you can use the Vertex AI Pipeline dashboard in your Google Cloud Console. This dashboard provides insights into the pipeline's progress, logs, and any potential issues.

4. **Test the Application in the Playground**

   You are now ready to test your RAG application with Vertex AI Search locally.
   To do that you can follow the instructions in the [root readme](../../../README.md#installation).

   1. Navigate to the root folder & install the required dependencies:

      ```bash
      poetry install --with streamlit,jupyter
      ```

   2. Configure your Google Cloud environment:

      ```bash
      export PROJECT_ID="YOUR_PROJECT_ID"
      gcloud config set project $PROJECT_ID
      gcloud auth application-default login
      gcloud auth application-default set-quota-project $PROJECT_ID
      ```

   3. Check your [app/chain.py](../../../app/chain.py) file to understand its content and verify the datastore ID and region are configured properly.

   4. Launch the playground:

      ```bash
      make playground
      ```

   5. Test your application!

   > **Note:** If you encounter the error `"google.api_core.exceptions.InvalidArgument: 400 The embedding field path: embedding not found in schema"` after the first ingestion, please wait a few minutes and try again.

5. **Setup Staging and Production:** Once you've validated the setup in your development environment, proceed to set up the Terraform infrastructure for your staging and production environments. Follow the instructions provided in the [deployment/README.md](../../../deployment/README.md) to configure and deploy the necessary resources.

   This ensures that your data ingestion pipeline is integrated into your CI/CD workflow. Once the setup is complete, any commit to the main branch will trigger the pipeline, updating your Vertex AI Search application with the latest data, and deploying the updated application and tests.

   Your CI/CD pipeline is now configured - any new commits will trigger the data ingestion, testing and deployment process automatically.

## Terraform Variables

This pattern introduces the following additional Terraform variables:

| Variable                    | Description                                                                        | Default Value           |
| --------------------------- | ---------------------------------------------------------------------------------- | ----------------------- |
| `search_engine_name`        | The name of the Vertex AI Search engine.                                           | `sample-search-engine`  |
| `datastore_name`            | The name of the Vertex AI Agent Builder Datastore.                                 | `sample-datastore`      |
| `vertexai_pipeline_sa_name` | The name of the service account used for Vertex AI Pipelines.                      | `vertexai-pipelines-sa` |
| `region_vertex_ai_search`   | The region for the Vertex AI Search engine. Can be one of "global", "us", or "eu". | `us`                    |
| `pipeline_cron_schedule`    | A cron expression defining the schedule for automated data ingestion.              | `0 0 * * 0`             |

These variables are defined in the `deployment/terraform/variables.tf` and `deployment/terraform/dev/variables.tf` files and can be customized in your `deployment/terraform/vars/env.tfvars` and `deployment/terraform/dev/vars/env.tfvars` files respectively.
