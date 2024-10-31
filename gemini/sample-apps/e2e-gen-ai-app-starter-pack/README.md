# 🚀 End-to-End Gen AI App Starter Pack 🚀

> **From Prototype to Production in Minutes.**

|                                                                 |                                                                                                                                      |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Authors**                                                     | [Elia Secchi](https://github.com/eliasecchig), [Lorenzo Spataro](https://github.com/lspataroG)                                       |
| [**1-Minute Video Overview**](https://youtu.be/D_VQYTczBpc)     | [<img src="https://img.youtube.com/vi/D_VQYTczBpc/maxresdefault.jpg" width="100" alt="Preview Video">](https://youtu.be/D_VQYTczBpc) |
| [**20-Minute Video Walkthrough**](https://youtu.be/kwRG7cnqSu0) | [<img src="https://img.youtube.com/vi/kwRG7cnqSu0/maxresdefault.jpg" width="100" alt="Preview Video">](https://youtu.be/kwRG7cnqSu0) |

This repository provides a template starter pack for building a Generative AI application on Google Cloud.

We provide a comprehensive set of resources to guide you through the entire development process, from prototype to production.

This is a suggested approach, and **you can adapt it to fit your specific needs and preferences**. There are multiple ways to build Gen AI applications on Google Cloud, and this template serves as a starting point and example.

## High-Level Architecture

This starter pack covers all aspects of Generative AI app development, from prototyping and evaluation to deployment and monitoring.

![High Level Architecture](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/high_level_architecture.png "Architecture")

## What's in this Starter Pack?

<details>
<summary><b>A prod-ready FastAPI server</b></summary>

| Description                                                                                                                                                                                                       | Visualization                                                                                                                      |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| The starter pack includes a production-ready FastAPI server with a real-time chat interface, event streaming, and auto-generated docs. It is designed for scalability and easy integration with monitoring tools. | ![FastAPI docs](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/fastapi_docs.png) |

</details>

<details>
<summary><b>Ready-to-use AI patterns</b></summary>

| Description                                                                                                                                                                                                                                                                                                                                             | Visualization                                                                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Start with a variety of common patterns: this repository offers examples including a basic conversational chain, a production-ready RAG (Retrieval-Augmented Generation) chain developed with Python, and a LangGraph agent implementation. Use them in the application by changing one line of code. See the [Readme](app/README.md) for more details. | ![patterns available](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/patterns_available.png) |

</details>

<details>
<summary><b>Integration with Vertex AI Evaluation and Experiments</b></summary>

| Description                                                                                                                              | Visualization                                                                                                                                      |
| ---------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| The repository showcases how to evaluate Generative AI applications using tools like Vertex AI rapid eval SDK and Vertex AI Experiments. | ![Vertex AI Rapid Eval](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/vertex_ai_rapid_eval.png) |

</details>

<details>
<summary><b>Unlock Insights with Google Cloud Native Tracing & Logging</b></summary>

| Description                                                                                                                                                                                     | Visualization                                                                                                                            |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Seamlessly integrate with OpenTelemetry, Cloud Trace, Cloud Logging, and BigQuery for comprehensive data collection, and log every step of your Gen AI application to unlock powerful insights. | ![Tracing Preview](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/tracing_preview.png) |

</details>

<details>
<summary><b>Monitor Responses from the application</b></summary>

| Description                                                                                                                                                                                                                                        | Visualization                                                                                                                   |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Monitor your Generative AI application's performance. We provide a Looker Studio [dashboard](https://lookerstudio.google.com/u/0/reporting/fa742264-4b4b-4c56-81e6-a667dd0f853f) to monitor application conversation statistics and user feedback. | ![Dashboard1](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/dashboard_1.png) |
| We can also drill down to individual conversations and view the messages exchanged.                                                                                                                                                                | ![Dashboard2](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/dashboard_2.png) |

</details>

<details>
<summary><b>CICD and Terraform</b></summary>

| Description                                                                                                                                                                                                                                                                      | Visualization                                                                                                      |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Streamline your deployments with Cloud Build. Enhance reliability through automated testing. The template includes implementation of unit, integration, and load tests, and a set of Terraform resources for you to set up your own Google Cloud project in a matter of minutes. | ![cicd](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/cicd.png) |

</details>

<details>
<summary><b>A comprehensive UI Playground</b></summary>

| Description                                                                                                                                                 | Visualization                                                                                                                          |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Experiment with your Generative AI application in a feature-rich playground, including chat curation, user feedback collection, multimodal input, and more! | ![Streamlit View](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/streamlit_view.png) |

</details>

## Getting Started

### Prerequisites

- Python >=3.10,<3.13
- Google Cloud SDK installed and configured
- [Poetry](https://python-poetry.org/docs/#installation) for dependency management

### Download the starter pack

```bash
gsutil cp gs://e2e-gen-ai-app-starter-pack/app-starter-pack.zip . && unzip app-starter-pack.zip && cd app-starter-pack
```

Use the downloaded folder as a starting point for your own Generative AI application.

### Installation

Install required packages using Poetry:

```bash
poetry install --with streamlit,jupyter
```

### Setup

Set your default Google Cloud project and region:

```bash
export PROJECT_ID="YOUR_PROJECT_ID"
gcloud config set project $PROJECT_ID
gcloud auth application-default login
gcloud auth application-default set-quota-project $PROJECT_ID
```

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `make playground`    | Start the backend and frontend for local playground execution                               |
| `make test`          | Run unit and integration tests                                                              |
| `make load_test`     | Execute load tests (see [tests/load_test/README.md](tests/load_test/README.md) for details) |
| `poetry run jupyter` | Launch Jupyter notebook                                                                     |

For full command options and usage, refer to the [Makefile](Makefile).

## Usage

1. **Prototype Your Chain:** Build your Generative AI application using different methodologies and frameworks. Use Vertex AI Evaluation for assessing the performance of your application and its chain of steps. **See [`notebooks/getting_started.ipynb`](notebooks/getting_started.ipynb) for a tutorial to get started building and evaluating your chain.**
2. **Integrate into the App:** Import your chain into the app. Edit the `app/chain.py` file to add your chain.
3. **Playground Testing:** Explore your chain's functionality using the Streamlit playground. Take advantage of the comprehensive playground features, such as chat history management, user feedback mechanisms, support for various input types, and additional capabilities. You can run the playground locally with the `make playground` command.
4. **Deploy with CI/CD:** Configure and trigger the CI/CD pipelines. Edit tests if needed. See the [deployment section](#deployment) below for more details.
5. **Monitor in Production:** Track performance and gather insights using Cloud Logging, Tracing, and the Looker Studio dashboard. Use the gathered data to iterate on your Generative AI application.

## Deployment

### Dev Environment

You can test deployment towards a Dev Environment using the following command:

```bash
gcloud run deploy genai-app-sample --source . --project YOUR_DEV_PROJECT_ID
```

The repository includes a Terraform configuration for the setup of the Dev Google Cloud project.
See [deployment/README.md](deployment/README.md) for instructions.

### Production Deployment with Terraform

![Deployment Workflow](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/deployment_workflow.png)

**Quick Start:**

1. Enable required APIs in the CI/CD project.

   ```bash
   gcloud config set project YOUR_CI_CD_PROJECT_ID
   gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
   ```

2. Create a Git repository (GitHub, GitLab, Bitbucket).
3. Connect to Cloud Build following [Cloud Build Repository Setup](https://cloud.google.com/build/docs/repositories#whats_next).
4. Configure [`deployment/terraform/vars/env.tfvars`](deployment/terraform/vars/env.tfvars) with your project details.
5. Deploy infrastructure:

   ```bash
   cd deployment/terraform
   terraform init
   terraform apply --var-file vars/env.tfvars
   ```

6. Perform a commit and push to the repository to see the CI/CD pipelines in action!

For detailed deployment instructions, refer to [deployment/README.md](deployment/README.md).

## Contributing

Contributions are welcome! See the [Contributing Guide](CONTRIBUTING.md).

## Feedback

We value your input! Your feedback helps us improve this starter pack and make it more useful for the community.

### Getting Help

If you encounter any issues or have specific suggestions, please first consider [raising an issue](https://github.com/GoogleCloudPlatform/generative-ai/issues) on our GitHub repository.

### Share Your Experience

For other types of feedback, or if you'd like to share a positive experience or success story using this starter pack, we'd love to hear from you! You can reach out to us at [e2e-gen-ai-app-starter-pack@google.com](mailto:e2e-gen-ai-app-starter-pack@google.com).

Thank you for your contributions!

## Disclaimer

This repository is for demonstrative purposes only and is not an officially supported Google product.
