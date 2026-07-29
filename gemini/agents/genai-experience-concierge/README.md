<!-- markdownlint-disable MD033 -->

# Gen AI Experience Concierge

## Introduction

Gen AI Experience Concierge is a collection of agent design pattern implementations. All design patterns are built using the LangGraph framework for agent orchestration and session management.

## Contents

For self-contained notebooks for interactively building each agent design pattern, navigate to the [agent-design-patterns/](./agent-design-patterns/) directory. The readme provides background and visualizations of each design pattern, including:

- A chat assistant with a guardrail classifier layer ([reference](./agent-design-patterns/README.md#guardrail-classifier-agent))
- A multi-agent chat assistant with an intent detection layer to route to experts ([reference](./agent-design-patterns/README.md#semantic-router-agent)).
- A chat assistant with function calling streaming capabilities, grounded on a mock retail dataset ([reference](./agent-design-patterns/README.md#function-calling-agent)).
- A multi-agent chat assistant for generating research plans, executing them and reflecting on the results ([reference](./agent-design-patterns/README.md#task-planner))

We have also packaged these implementations as a "click-to-deploy" application that serves each LangGraph agent on a FastAPI Server with a Streamlit frontend demo. The agent server is compatible with the [LangGraph Cloud API spec](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html) (to learn more about why this is useful, visit this [section](#why-use-the-langgraph-cloud-api-spec)).

For instructions on deployment, please navigate to the [End-to-end Deployment](#end-to-end-deployment-) section. The command-line tool for automated deployment is defined in the [scripts/cli](./scripts/cli/) folder.

The source code for the deployable demo is broken into the following structure:

```bash
langgraph-demo
│
├── backend                        ; Backend agent server
│   ├── concierge
│   │   ├── agents                 ; All agent definitions
│   │   ├── langgraph_server       ; LangGraph -> fastapi.APIRouter adapter
│   │   ├── nodes                  ; All LangGraph node definitions
│   │   │   └── task_planning
│   │   │       └── ops
│   │   └── tools                  ; LLM tool definitions
│   └── notebooks                  ; Notebooks to interact with agents
│
├── frontend                       ; Frontend Streamlit server
│   └── concierge_ui
│       └── agents                 ; Chat handlers for each agent
│
└── terraform                      ; Infrastructure code for deployment
```

The [backend](./langgraph-demo/backend/) and [frontend](./langgraph-demo/frontend/) directories each contain their own readme for a deeper dive on local environment setup.

## Why use the LangGraph Cloud API spec?

The LangGraph Cloud API spec is used by the standard LangGraph client SDKs to interact with deployed agents. A minimal subset of endpoints required by the [langgraph_sdk.RemoteGraph](https://langchain-ai.github.io/langgraph/reference/remote_graph/) interface. The `RemoteGraph` interface supports the same protocol used by `CompiledGraph` (the local LangGraph class). Instead of designing custom routes for each new agent, you can rely on a consistent, predictable interface for interacting with LangGraph agents during development and deployment. This also benefits downstream teams (such as frontend developers) that need to invoke deployed agents. By supporting the LangGraph remote client, downstream teams only need to learn one client implementation and can quickly integrate newly deployed agents.

Currently, LangGraph only offers a solution for LangGraph Cloud API-compatible deployments on the managed LangGraph Platform. To enable this for self-hosted deployments, we wrote a small module ([source code](./langgraph-demo/backend/concierge/langgraph_server/)) to transform LangGraph agents into FastAPI routes. This doesn't support many of the premium features offered by the LangGraph Platform but is sufficient for using the `RemoteGraph` client.

To demonstrate the portability of this approach, the Streamlit frontend demo hosts 5 different chat agents with the only dependency being the standard `langgraph` package for calling the remote agents. The frontend implementations for each agent can be found in [this folder](./langgraph-demo/frontend/concierge_ui/agents).

## Quickstart Demo ✨

### Environment Setup

Clone the repository and ensure that the Google Application Default Credentials are configured. You can do this by running the following commands:

```bash
# Clone repository and navigate to project root directory
git clone https://github.com/GoogleCloudPlatform/generative-ai.git
cd generative-ai/gemini/agents/genai-experience-concierge

# Set up Google Application Default Credentials
gcloud auth login
gcloud auth application-default login
```

### (Optional) Create the Cymbal Retail dataset

The function calling demo agent requires a BigQuery dataset and embedding model connection to exist to query a fictional retail dataset. This is automatically created during demo deployment, but must be manually created if the demo project doesn't exist. To manually create these tables and embedding model, you can run this command:

```bash
uv run --frozen concierge langgraph create-dataset --project-id $PROJECT_ID
```

### Start the agent backend server

To start the backend server, open a new terminal window, navigate to `langgraph-demo/backend` and run:

```bash
CONCIERGE_PROJECT=$PROJECT_ID uv run --frozen uvicorn concierge.server:app \
  --port 3000 \
  --reload
```

You can view the swagger documentation at [https://localhost:3000/docs](https://localhost:3000/docs). The docs include separate sections for each agent's router.

<div align="center" width="100%">
  <img src="https://storage.googleapis.com/github-repo/generative-ai/gemini/agents/genai-experience-concierge/langgraph-fastapi.png" alt="Example agent server swagger docs" width="75%" />
</div>

### Start the Streamlit frontend server

To start the frontend server, open a new terminal window, navigate to `langgraph-demo/frontend` and run:

```bash
uv run --frozen streamlit run concierge_ui/server.py \
  --server.port 8080 \
  --server.runOnSave true
```

Navigate to [https://localhost:8080/](https://localhost:8080/) to use the Streamlit demos.

<div align="center" width="100%">
  <img src="https://storage.googleapis.com/github-repo/generative-ai/gemini/agents/genai-experience-concierge/langgraph-streamlit-home.png" alt="Example streamlit home page" width="75%" />
</div>

## End-to-End Deployment 🚀

The end-to-end deployment tool, `concierge langgraph deploy`, will create a new demo project, provision necessary infrastructure, and deploy the backend LangGraph server and frontend Streamlit app.

### Google Cloud Architecture

<div align="center" width="100%">
  <img src="https://storage.googleapis.com/github-repo/generative-ai/gemini/agents/genai-experience-concierge/langgraph-architecture.png" alt="Gen AI Experience Concierge LangGraph Demo Architecture" width="75%" />
</div>

### Set up a seed project

The click-to-deploy LangGraph demo uses the [project-factory](https://registry.terraform.io/modules/terraform-google-modules/project-factory/google/latest) terraform module to automate the creation of a demo project and infrastructure provisioning. The module provides a helper script ([documentation](https://github.com/terraform-google-modules/terraform-google-project-factory?tab=readme-ov-file#script-helper)) to check that the seed project is configured correctly. It is recommended to run this script before running the deployment to ensure there won't be any errors.

### Configure the LangGraph demo deployment

Arguments to the CLI can either be provided on the command line or via a config file. An example config file might look like:

```yaml
langgraph:
  deploy:
    # Seed project to use for the terraform project factory.
    seed_project: seed-project-id
    # Target demo project to create.
    project_id: target-project-id
    # Billing account to attach to the target project.
    billing_account: 000000-000000-000000
    # Support email to appear in the OAuth consent screen.
    support_email: support@email.com
    # Terraform state bucket for infrastructure provisioning
    state_bucket: bucket-name
    # demo users that should have access to the deployed frontend demo.
    demo_users: ["group:test@email.com"]

    # (Optional) state bucket prefix
    state_bucket_prefix: concierge/langgraph
    # (Optional) organization ID to create the target project
    org_id: 000000000000
    # (Optional) folder ID to create the target project
    folder_id: 000000000000
```

### Deploy the LangGraph demo

Now that the seed project and configuration has been created, the demo can be deployed with the following command:

```bash
uv run --frozen concierge -f $CONFIG_YAML_FILE langgraph deploy
```

## Authors

[Enrique Chan](mailto:enriq@google.com): Project Lead

[Pablo Gaeta](mailto:pablogaeta@google.com): Engineer Lead

[Afshaan Mazagonwalla](mailto:afshaanmaz@google.com): Engineer

[Aadila Jasmin](mailto:aadilajasmin@google.com): Engineer

[Ahmad Khan](mailto:ahmadkh@google.com): Engineer

## Contributing

Contributions welcome! If you have any feedback or suggestions of agent design patterns to implement, please reach out to [genai-experience-concierge@google.com](mailto:genai-experience-concierge@google.com). See also the repository [Contributing Guide](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/CONTRIBUTING.md).

## Disclaimer

This demo is not an officially supported Google product. The code in this repository is for demonstrative purposes only.
