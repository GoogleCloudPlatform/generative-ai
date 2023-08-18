# Setup instructions to use Generative AI on Google Cloud

This folder contains instructions on:

- Setting up your Google Cloud project
- Notebook environments
  - Setting up Colab
  - Setting up Vertex AI Workbench
- Python SDK for Vertex AI

## Setting up your Google Cloud project

1. [Select or create a Google Cloud project](https://console.cloud.google.com/cloud-resource-manager).
When you first create an account, you get a $300 free credit towards your compute/storage costs.

2. [Make sure that billing is enabled for your project](https://cloud.google.com/billing/docs/how-to/modify-project).

3. [Enable the Vertex AI API](https://console.cloud.google.com/flows/enableapi?apiid=aiplatform.googleapis.com).

## Notebook environments

### Colab

[Google Colab](https://colab.research.google.com/) allows you to write and execute Python in your browser with minimal setup.

To use Colab with this repo, please click on the "Open in Colab" link at the top of any notebook file in this repo to launch it in Colab. Then follow the instructions within.

For Colab you will need to authenticate so that you can use Google Cloud from Colab:

```py
from google.colab import auth
auth.authenticate_user()
```

When using the vertexai Python SDK, you will also need to initialize it with your GCP `project_id` and `location`:

```py
PROJECT_ID = "your-project-id"
LOCATION = "" #e.g. us-central1

import vertexai
vertexai.init(project=PROJECT_ID, location=LOCATION)
```

### Vertex AI Workbench

[Vertex AI Workbench](https://cloud.google.com/vertex-ai-workbench) is the JupyterLab notebook environment on Google Cloud, which enables you to create and customize notebook instances. You do not need extra authentication steps.

#### Creating your notebook instance on Vertex AI Workbench

To create a new JupyterLab instance on Vertex AI Workbench, follow the [instructions here to create a user-managed notebooks instance](https://cloud.google.com/vertex-ai/docs/workbench/user-managed/create-new).

#### Using this repository on Vertex AI Workbench

After launching the notebook instance, you can clone this repository in your JupyterLab environment. To do so, open a Terminal in JupyterLab. Then run the command below to clone the repository into your instance:

```sh
git clone https://github.com/GoogleCloudPlatform/generative-ai.git
```

## Python library

Install the latest Python SDK:

```sh
!pip install google-cloud-aiplatform --upgrade
```

You will need to initialize `vertexai` with your `project_id` and `location`:

```py
PROJECT_ID = "your-project-id"
LOCATION = "" #e.g. us-central1

import vertexai
vertexai.init(project=PROJECT_ID, location=LOCATION)
```
