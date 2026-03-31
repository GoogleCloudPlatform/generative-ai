# User Guide: Deploying an A2UI Agent to Cloud Run, Registering with Gemini Enterprise and Interacting with the Agent using A2UI components

This guide provides a comprehensive walkthrough of deploying an A2A
(Agent-to-Agent) enabled agent with **A2UI** extension, built with the Google
**Agent Development Kit (ADK)**, to Google **Cloud Run**. You can interact with
the agent by rich content A2UI components. You will also learn how to register
your deployed agent with Gemini Enterprise to make it discoverable and usable by
other agents.

## Introduction

This project provides a template for creating and deploying a powerful,
Gemini-based agent that can communicate with other agents using the A2A protocol
and can display A2UI components. By the end of this guide, you will have a
publicly accessible agent running on Cloud Run and can display A2UI components
on Gemini Enterprise UI.

## Prerequisites

Before you begin, ensure you have the following installed and configured:

*   **Google Cloud SDK:**
    [Install the gcloud CLI](https://cloud.google.com/sdk/docs/install).
*   **A Google Cloud Project:** You will need a project with billing enabled to
    deploy to Cloud Run.
*   **Authentication:** Log in to your Google Cloud account and set up
    application default credentials:
    ```bash
    gcloud config set project <YOUR_PROJECT_ID>
    gcloud auth login
    gcloud auth application-default login
    ```

## Project Structure

This directory contains all the necessary files for deploying the agent:

*   `main.py`: The main entry point for the application. It initializes and runs
    the FastAPI web server.
*   `gemini_agent.py`: Contains the core logic and definition of the Gemini
    agent, including its system instructions and tools.
*   `agent_executor.py`: Handles the execution of agent tasks by interfacing
    with the Google Agent Development Kit (ADK).
*   `requirements.txt`: A list of all the Python dependencies required for the
    agent to run.
*   `Procfile`: Specifies the command to start the web server, used by Google
    Cloud Run during deployment.
*   `deploy.sh`: A shell script that automates the entire deployment process.

## The ADK Agent (`gemini_agent.py`)

The heart of our application is the `GeminiAgent` class in `gemini_agent.py`.
This class inherits from the `LlmAgent` provided by the Google ADK, and it's
where you define your agent's identity, capabilities, and tools.

### Agent Identity

The agent's identity is defined by its `name` and `description`. You can
customize these to reflect your agent's purpose:

```python
class GeminiAgent(LlmAgent):
    """An agent powered by the Gemini model via Vertex AI."""

    # --- AGENT IDENTITY ---
    name: str = "gemini_agent"
    description: str = "A helpful assistant powered by Gemini."
```

### System Instructions

The `instructions` variable within the `get_ui_prompt` method sets the agent's
system prompt. This is where you can define the agent's personality, its role,
and any constraints on its behavior.

```python
class GeminiAgent(LlmAgent):
    def __init__(self, **kwargs):
        # --- SET YOUR SYSTEM INSTRUCTIONS HERE ---
        instructions = """
            You are a helpful contact lookup assistant. Your final output MUST be a a2ui UI JSON response.


        You can use the get_contact_info tool to find the contact card of a person.
        """
```

### Tools

The ADK allows you to extend your agent's capabilities by giving it tools. In
this example, we have a `get_contact_info` function that the agent can call. You
can add your own tools by defining a Python function and registering it in the
`tools` list.

```python
# --- DEFINE YOUR TOOLS HERE ---
def get_contact_info(name: str = None) -> str:
  """Gets contact information for a person.

  Args:
      name: The name of the person to look up. If None, returns a list of
        suggested contacts.

  Returns:
      JSON string containing contact details.
  """
  ......

class GeminiAgent(LlmAgent):
    def __init__(self, **kwargs):
        # --- REGISTER YOUR TOOLS HERE ---
        tools = [
            get_weather
        ]
```

## The A2A Executor (`agent_executor.py`)

The `AdkAgentToA2AExecutor` class in `agent_executor.py` is the bridge between
the A2A framework and your ADK agent. It implements the `AgentExecutor`
interface from the A2A library and is responsible for handling incoming requests
and invoking your agent.

The `execute` method is the core of this class. It performs the following steps:

1.  **Retrieves the user's query** from the `RequestContext`.
2.  **Manages the task lifecycle**, creating a new task if one doesn't exist.
3.  **Manages the session**, creating a new session if one doesn't exist.
4.  **Invokes the ADK Runner** by calling `self._runner.run_async()`, passing
    the user's query.
5.  **Streams the response** back to the A2A framework, updating the task with
    the final result.

This executor ensures that your ADK-based agent can seamlessly communicate
within the A2A protocol.

## Deployment

The `deploy.sh` script automates the deployment process. To deploy your agent,
navigate to this directory and run the script with your Google Cloud Project ID
and a name for your new service. You can also optionally specify the Gemini
model to use.

```bash
chmod +x deploy.sh
./deploy.sh <YOUR_PROJECT_ID> <YOUR_SERVICE_NAME> [MODEL_NAME]
```

*   `MODEL_NAME`: Optional. Can be `gemini-2.5-pro` or `gemini-2.5-flash`.
    Defaults to `gemini-2.5-flash` if not specified.

For example:

```bash
# Deploy with the default gemini-2.5-flash model
chmod +x  deploy.sh
./deploy.sh  my-gcp-project my-gemini-agent

# Deploy with the gemini-2.5-pro model
./deploy.sh  my-gcp-project my-gemini-agent gemini-2.5-pro
```

The script will:

1.  **Build a container image** from your source code.
2.  **Push the image** to the Google Container Registry.
3.  **Deploy the image** to Cloud Run.
4.  **Set environment variables**, including the `MODEL` and the public
    `AGENT_URL` of the service itself.

Once the script completes, it will print the public URL of your deployed agent.

## Registration with Gemini Enterprise

Now that your agent is deployed, you need to register it with Gemini Enterprise
to make it discoverable. This is done programmatically using the Discovery
Engine API.

**1. Get your Gemini Enterprise Engine ID:**

You can find your Engine ID in the Google Cloud Console.

**2. Register the agent:**

Execute the following `curl` command, replacing the placeholders with your own
values:

```bash
curl -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json" https://discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/collections/default_collection/engines/ENGINE_ID/assistants/default_assistant/agents -d '{
  "name": "AGENT_NAME",
  "displayName": "AGENT_DISPLAY_NAME",
  "description": "AGENT_DESCRIPTION",
  "a2aAgentDefinition": {
     "jsonAgentCard": "{\"protocolVersion\": \"v1.0\", \"name\": \"AGENT_NAME\", \"description\": \"AGENT_DESCRIPTION\", \"url\": \"AGENT_URL\", \"version\": \"1.0.0\", \"capabilities\": {\"streaming\": true, \"extensions\": [{\"uri\": \"https://a2ui.org/a2a-extension/a2ui/v0.8\", \"description\": \"Ability to render A2UI\", \"required\": false, \"params\": {\"supportedCatalogIds\": [\"https://a2ui.org/specification/v0_8/standard_catalog_definition.json\"]}}]}, \"skills\": [], \"defaultInputModes\": [\"text/plain\"], \"defaultOutputModes\": [\"text/plain\"], \"authentication\": {\"type\": \"http\", \"scheme\": \"bearer\", \"tokenFromEnv\": \"MY_AGENT_TOKEN\"}}"
  }
}'
```

**Placeholder Descriptions:**

*   `PROJECT_NUMBER`: Your Google Cloud project number.
*   `LOCATION`: The location of your Discovery Engine instance (e.g., `global`).
*   `ENGINE_ID`: The ID of your Gemini Enterprise engine.
*   `AGENT_NAME`: A unique name for your agent.
*   `AGENT_DISPLAY_NAME`: The name that will be displayed in the Gemini
    Enterprise UI.
*   `AGENT_DESCRIPTION`: A brief description of your agent's capabilities.
*   `AGENT_URL`: The public URL of your deployed agent.
*   `CREDENTIAL_KEY`: The key for your authentication credentials (e.g.,
*   `MY_AGENT_TOKEN`: The name of an environment variable that Gemini Enterprise
    will read to get the bearer token for authentication. **Note on
    Credentials:** At execution time, when Gemini Enterprise talks to the agent,
    **Note on Authentication:** This example uses bearer token authentication.
    Gemini Enterprise will read the environment variable specified in
    `tokenFromEnv` (e.g., `MY_AGENT_TOKEN`) to get the token. It will then send
    an HTTP `Authorization` header to your agent with the value `Bearer
    <token_from_env_variable>`. **3. Locate the agent on the Gemini Enterprise
    UI:**

Your agent can be found in the Gemini Enterprise UI. Once you click it, you can
interact with the agent. Send queries like "Find Alex contact card", or "List
all contacts" and you will see A2UI components being rendered.

### IAM Support for Agents Running on Cloud Run

When the agent is deployed on Cloud Run (when the `AGENT_URL` ends with
"run.app"), Gemini Enterprise attempts IAM authentication when talking to the
agent. For this to work, you should grant the "Cloud Run Invoker" role to the
following principal in the project where Cloud Run is running:

`service-PROJECT_NUMBER@gcp-sa-discoveryengine.iam.gserviceaccount.com`

### Unregistering the Agent (Optional)

The following command can be used to unregister the agent:

```bash
curl -X DELETE -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json" https://discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/collections/default_collection/engines/ENGINE_ID/assistants/default_assistant/agents/AGENT_ID
```

## Conclusion

Congratulations! You have successfully deployed an A2A-enabled agent with A2UI
capacity to Cloud Run and registered it with Gemini Enterprise. Your agent is
now ready to interact with other agents in the A2A ecosystem. You can further
customize your agent by adding more tools, refining its system instructions, and
enhancing its capabilities.
