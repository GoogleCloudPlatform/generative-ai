# Setup instructions to use Generative AI on Google Cloud

This folder contains instructions on how to get set up with Generative AI on Google Cloud.

## Notebook environments

### Colab
Please follow the instructions directly in the notebook (.ipynb) files, and note that you will need to run the following cell to authenticates your Colab environment with your Google Cloud account.
```
from google.colab import auth
auth.authenticate_user()
```

### Vertex AI Workbench
[Vertex AI Workbench](https://cloud.google.com/vertex-ai-workbench) is the managed notebook environment on Google Cloud, which enables you to create and customize notebook instances. You do not need extra authentication steps.

#### Creating your notebook instance on Vertex AI Workbench
To create an instance, follow the [instructions here to Create a user-managed notebooks instance](https://cloud.google.com/vertex-ai/docs/workbench/user-managed/create-new). Unless specified in the notebook, you can use default settings when creating your notebook instance.

#### Using this repository on Vertex AI Workbench
After launching the notebook instance, you can clone this repository in your JupyterLab environment. To do so, open a Terminal in JupyterLab. Then run the command below to clone the repository into your instance:

```
git clone https://github.com/GoogleCloudPlatform/generative-ai.git
```

## Python library

Install the latest Python SDK:
```
!pip install google-cloud-aiplatform --upgrade
```

You will need to initialize `vertexai` with your `project_id` and `location`:

```
PROJECT_ID = "your-project-id"
LOCATION = "" #e.g. us-central1

import vertexai
vertexai.init(project=PROJECT_ID, location=LOCATION)
```
