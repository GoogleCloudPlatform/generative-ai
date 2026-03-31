# Register an A2UI Agent deployed on Vertex AI Agent Engine with Gemini Enterprise

This sample demonstrates how to deploy an A2UI Agent on **Agent Engine** and
register on **Gemini Enterprise**.

## Overview

High level steps:

-   Config Authorization
-   Setup environment variables
-   Develop A2UI agent with ADK + A2A (sample code provided)
-   Deploy the agent to Agent Engine
-   Register the agent on Gemini Enterprise

## Config Authorization

Check **Before you begin** section and follow **Obtain authorization details**
section on
[Register and manage A2A agents](https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-a2a-agent).
Download JSON that looks like:

```
{
    "web": {
        "client_id": "<client id>",
        "project_id": "<Google Cloud project id>",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "<secret>",
        "redirect_uris": [
            "https://vertexaisearch.cloud.google.com/oauth-redirect",
            "https://vertexaisearch.cloud.google.com/static/oauth/oauth.html"
        ]
    }
}
```

NOTE: For this deployment, you can skip the rest of **Register and manage A2A
agents** page.

Replace **YOUR_CLIENT_ID** with `client_id` which can be found in the downloaded
json and save the following as **authorizationUri**

```
https://accounts.google.com/o/oauth2/v2/auth?client_id=<YOUR_CLIENT_ID>&redirect_uri=https%3A%2F%2Fvertexaisearch.cloud.google.com%2Fstatic%2Foauth%2Foauth.html&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcloud-platform&include_granted_scopes=true&response_type=code&access_type=offline&prompt=consent
```

In your console, run this:

```
curl -X POST \
   -H "Authorization: Bearer $(gcloud auth print-access-token)" \
   -H "Content-Type: application/json" \
   -H "X-Goog-User-Project: <YOUR_PROJECT_ID>" \
   "https://<ENDPOINT_LOCATION>-discoveryengine.googleapis.com/v1alpha/projects/<YOUR_PROJECT_ID>/locations/<LOCATION>/authorizations?authorizationId=<AUTH_ID>" \
   -d '{
      "name": "projects/<YOUR_PROJECT_ID>/locations/<LOCATION>/authorizations/<AUTH_ID>",
      "serverSideOauth2": {
         "clientId": "<OAUTH_CLIENT_ID>",
         "clientSecret": "<OAUTH_CLIENT_SECRET>",
         "authorizationUri": "<OAUTH_AUTH_URI>",
         "tokenUri": "<OAUTH_TOKEN_URI>"
      }
   }'
'
```

Replace the following:

-   **YOUR_PROJECT_ID**: the ID of your project. There are 3 occasions
-   **ENDPOINT_LOCATION**: the multi-region for your API request. Specify one of
    the following values:
    -   *us* for the US multi-region
    -   *eu* for the EU multi-region
    -   *global* for the Global location
-   **LOCATION**: the multi-region of your data store: *global*, *us*, or *eu*.
    There are 2 occasions
-   **AUTH_ID**: The ID of the authorization resource. This is an arbitrary
    alphanumeric ID that you define. You need to reference this ID later when
    registering an Agent that requires OAuth support. There are 2 occasions.
-   **OAUTH_CLIENT_ID**: copy `client_id` from the downloaded JSON.
-   **OAUTH_CLIENT_SECRET**: copy `client_secret` from the downloaded JSON.
-   **OAUTH_AUTH_URI**: the value of **authorizationUri**. See above.
-   **OAUTH_TOKEN_URI**: copy `token_uri` from the downloaded JSON.

NOTE: if `$(gcloud auth print-access-token)` does not work for you, replace it
with `$(gcloud auth application-default print-access-token)` and try again.

As result, you will get **AGENT_AUTHORIZATION** like this:

```
projects/PROJECT_NUMBER/locations/global/authorizations/<AUTH_ID>
```

The value will be used as an environment variable described below.

NOTE: if you already have an agent that is deployed to Agent Engine, skip to
**Manually Register An Agent** section.

## Setup Environment Variables

1.  **Copy `.env.example`:** Duplicate the `.env.example` file and rename it to
    `.env`.
    -   `cd /path/to/a2ui_on_agentengine`
    -   `cp .env.example .env`
2.  **Fill `.env`:** Update the `.env` file with your specific Google Cloud
    project details:
    *   `PROJECT_ID`: Your Google Cloud Project ID.
    *   `LOCATION`: The Google Cloud region you want to deploy the agent in (e.g.,
        `us-central1`). This location is **not** the same as the *location* used
        in the command above.
    *   `STORAGE_BUCKET`: A Google Cloud Storage bucket name for staging. It
        starts with **"gs://"**.
    *   `GEMINI_ENTERPRISE_APP_ID`: Your Gemini Enterprise Application ID. You
        can create a new App or use an existing one on Google Cloud Gemini Enterprise.
    *   `AGENT_AUTHORIZATION`: the value **AGENT_AUTHORIZATION** obtained above.

## Running the Script

The `main.py` script performs the following actions:

1.  Initializes the Vertex AI client.
2.  Defines a sample "Contact Card Agent" skill and creates an agent card.
3.  Creates a local `A2aAgent` instance.
4.  Deploys the agent to Vertex AI Agent Engine (`client.agent_engines.create`).
5.  Fetches the deployed agent's card.
6.  Registers the agent on Gemini Enterprise using the Discovery Engine API.

To run the script using `uv`:

1.  **Navigate to the script directory:**
    -   `cd /path/to/a2ui_on_agentengine`
2.  **Create and activate a virtual environment:**
    -   `uv venv source`
    -   `.venv/bin/activate`
3.  **Install dependencies:**
    -   `uv sync`
4.  **Run the script:**
    -   `uv run main.py`
    -   It may take 5-10 minutes to finish.

## Customization

To build your own agent, you will need to:

*   Implement your agent's logic, by modifying or replacing `agent_executor.py`
    and the `AdkAgentToA2AExecutor` class.
*   Adjust the `agent_name`, `display_name`, and `description` when calling
    `_register_agent_on_gemini_enterprise` in `main.py`.

## Manually Register An Agent

If you have an Agent that is already deployed to Agent Engine, you can manually
register it on Gemini Enterprise without running "main.py" script.

1.  Complete **Config Authorization** section above.
2.  Open Google Cloud **Gemini Enterprise**.
3.  Click on the **App** you want to register your agent.
    -   If you don't see the app being listed, click **Edit** to switch location
4.  Select **Agents** from the left nav bar.
5.  Click **Add agent** and select **Add** on **A2A** card.
6.  Copy this following JSON to the "Agent Card JSON" input box.

    ```
    {
      "name": "Test Contact Card Agent",
      "url": "https://<LOCATION>-aiplatform.googleapis.com/v1beta1/<RESOURCE_NAME>/a2a",
      "description": "A helpful assistant agent that can find contact card s.",
      "skills": [
        {
          "description": "A helpful assistant agent that can find contact cards.",
          "tags": [
            "Contact-Card"
          ],
          "name": "Contact Card Agent",
          "examples": [
            "Who is John Doe?",
            "List all contact cards."
          ],
          "id": "contact_card_agent"
        }
      ],
      "version": "1.0.0",
      "capabilities": {
        "streaming": false,
        "extensions": [
          {
            "uri": "https://a2ui.org/a2a-extension/a2ui/v0.8",
            "description": "Ability to render A2UI",
            "required": false,
            "params": {
              "supportedCatalogIds": [
                "https://a2ui.org/specification/v0_8/standard_catalog_definition.json"
              ]
            }
          }
        ]
      },
      "protocolVersion": "0.3.0",
      "defaultOutputModes": [
        "application/json"
      ],
      "defaultInputModes": [
        "text/plain"
      ],
      "supportsAuthenticatedExtendedCard": true,
      "preferredTransport": "HTTP+JSON"
    }
    ```

    Replace **LOCATION** and **RESOURCE_NAME**.

    -   LOCATION is where you deploy your agent. For example; us-central1.
    -   RESOURCE_NAME can be found on Google Cloud **Agent Engine**: click the agent;
        click **Service Configuration**; select **Deployment details**; copy
        **Resource name**.

    Update *name*, *description*, *skills*, *version* as needed. Leave other
    values unchanged.

7.  Click **Preview Agent Details**

8.  Click **Next**

9.  Fill the **Agent authorization** form:

    -   Copy `client_id`, `client_secret`, `token_uri` from the downloaded JSON.
    -   Copy **authorizationUri** value from the above to **Authorization URL**.
    -   Leave **Scopes** field empty.
    -   Click **Finish**

## Test Your Agent

1.  Open Google Cloud Console and search for **"Gemini Enterprise"** and click on it.
2.  Open the project you used in the above setting.
3.  Click on the **App** you used to register your agent.
    -   If you don't see your app being listed, click **"Edit"** to switch
        location
4.  Select **"Agents"** from the left nav bar.
5.  Click the three-dot button on the **"Actions"** column and select
    **"Previwe"** menu.
6.  It will open Gemini Enterprise Agent page.
7.  Try queries like *"Find contact card of Sarah"*.
    -   If this is the first time you start a chat with the agent, it will ask
        for manual authorization.
8.  You should see a Contact Card being rendered on Gemini Enterprise.
