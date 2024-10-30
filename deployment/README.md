# Deployment README.md

This folder contains the infrastructure-as-code and CI/CD pipeline configurations for deploying a conversational Generative AI application on Google Cloud.

The application leverages [**Terraform**](http://terraform.io) to define and provision the underlying infrastructure, while [**Cloud Build**](https://cloud.google.com/build/) orchestrates the continuous integration and continuous deployment (CI/CD) pipeline.

## Deployment Workflow

![Deployment Workflow](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/deployment_workflow.png)

**Description:**

1. CI Pipeline (`deployment/ci/pr_checks.yaml`):

   - Triggered on pull request creation/update
   - Runs unit and integration tests

2. CD Pipeline (`deployment/cd/staging.yaml`):

   - Triggered on merge to `main` branch
   - Builds and pushes application to Artifact Registry
   - Deploys to staging environment (Cloud Run)
   - Performs load testing

3. Production Deployment (`deployment/cd/deploy-to-prod.yaml`):
   - Triggered after successful staging deployment
   - Requires manual approval
   - Deploys to production environment

## Setup

**Prerequisites:**

1. A set of Google Cloud projects:
   - Staging project
   - Production project
   - CI/CD project (can be the same as staging or production)
2. Terraform installed on your local machine
3. Enable required APIs in the CI/CD project. This will be required for the Terraform deployment:

   ```bash
   gcloud config set project $YOUR_CI_CD_PROJECT_ID
   gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
   ```

## Step-by-Step Guide

1. **Create a Git Repository using your favorite Git provider (GitHub, GitLab, Bitbucket, etc.)**

2. **Connect Your Repository to Cloud Build**
   For detailed instructions, visit: [Cloud Build Repository Setup](https://cloud.google.com/build/docs/repositories#whats_next).<br>

   ![Alt text](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/connection_cb.gif)

3. **Configure Terraform Variables**

   - Edit [`deployment/terraform/vars/env.tfvars`](../terraform/vars/env.tfvars) with your Google Cloud settings.

   | Variable               | Description                                                     | Required |
   | ---------------------- | --------------------------------------------------------------- | :------: |
   | prod_project_id        | **Production** Google Cloud Project ID for resource deployment. |   Yes    |
   | staging_project_id     | **Staging** Google Cloud Project ID for resource deployment.    |   Yes    |
   | cicd_runner_project_id | Google Cloud Project ID where CI/CD pipelines will execute.     |   Yes    |
   | region                 | Google Cloud region for resource deployment.                    |   Yes    |
   | host_connection_name   | Name of the host connection you created in Cloud Build          |   Yes    |
   | repository_name        | Name of the repository you added to Cloud Build                 |   Yes    |

   Other optional variables include: telemetry and feedback BigQuery dataset IDs, log filters, sink names, service account names, bucket name suffixes, artifact registry repository name, and various role assignments for Cloud Run and CICD.

4. **Deploy Infrastructure with Terraform**

   - Open a terminal and navigate to the Terraform directory:

   ```bash
   cd deployment/terraform
   ```

   - Initialize Terraform:

   ```bash
   terraform init
   ```

   - Apply the Terraform configuration:

   ```bash
   terraform apply --var-file vars/env.tfvars
   ```

   - Type 'yes' when prompted to confirm

After completing these steps, your infrastructure will be set up and ready for deployment!

## Dev Deployment

For End-to-end testing of the application, including tracing and feedback sinking to BigQuery, without the need to trigger a CI/CD pipeline.

After you edited the relative [`env.tfvars` file](../terraform/dev/vars/env.tfvars), follow the following instructions:

```bash
cd deployment/terraform/dev
terraform init
terraform apply --var-file vars/env.tfvars
```

Then deploy the application using the following command (from the root of the repository):

```bash
gcloud run deploy genai-app-sample --source . --project $YOUR_DEV_PROJECT_ID --service-account genai-app-sample-cr-sa@$YOUR_DEV_PROJECT_ID.iam.gserviceaccount.com
```

### End-to-end Demo video

<a href="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/template_deployment_demo.mp4">
  <img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/preview_video.png" alt="Watch the video" width="300"/>
</a>
