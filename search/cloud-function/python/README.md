# Vertex AI Search accessed via Google Cloud Functions

This example is based on the
[Python client for the Vertex AI Search API](https://cloud.google.com/generative-ai-app-builder/docs/libraries#client-libraries-usage-python),
which will get search results, snippets, metadata, and the LLM summary grounded
on search results. This is implemented in the `vertex_ai_search_client.py` file.

That functionality is exposed on a REST API which is implemented in `main.py`
intended to be deployed to a Google Cloud Function using an HTTPS trigger on a
Python 3 runtime;
[read more here](https://cloud.google.com/functions/docs/samples/functions-http-content#functions_http_content-python).

**[Read more about Vertex AI Search accessed via Google Cloud Functions](../)**

## Environment Variables

The following environment variables are required for both local development and
deployment:

- `PROJECT_ID`: Your Google Cloud project ID
- `LOCATION`: The location of your Vertex AI Search data store
- `DATA_STORE_ID`: The ID of your Vertex AI Search data store
- `ENGINE_DATA_TYPE`: Type of data in the engine (0-3)
- `ENGINE_CHUNK_TYPE`: Type of chunking used (0-3)
- `SUMMARY_TYPE`: Type of summary used (0-3)

## Local Development

### Setup

1. Ensure you have the Google Cloud SDK installed and configured.
2. Clone this repository and navigate to the project directory.
3. Set up your environment variables:

```bash
gcloud auth login
bash setup_env.sh
```

Alternatively, you can manually create and edit a `.env` file with the required
variables.

### Run locally

Run this code locally via **Functions Framework** or **Functions Emulator**;
[read more about running cloud functions locally](https://cloud.google.com/functions/docs/running/overview).

```bash
pip install -r requirements.txt
pip install functions-framework
functions-framework --target=vertex_ai_search
```

In a different terminal, execute a `POST` search query based on your data:

```bash
export SEARCH_TERM="What is the ... for ...?"
curl -m 310 -X POST localhost:8080 \
-H "Content-Type: application/json" \
-d "{\"search_term\": \"${SEARCH_TERM}\"}"
```

### Run tests

#### Unit tests

These tests mock the API interactions and should run quickly:

```bash
pip install pytest
pytest test_vertex_ai_search_client.py
```

#### Integration tests

These tests actually call the Vertex AI Search API and depend on your data
stores being configured in Vertex AI Search:

```bash
pip install pytest
pytest test_integration_vertex_ai_search_client.py
```

## Deployment

To deploy this function to Google Cloud:

1. Ensure you have set up the required environment variables (see Environment
   Variables section).
2. Run the following command:

```bash
gcloud functions deploy vertex_ai_search --runtime python39 --trigger-http --allow-unauthenticated
```

You will get back a URL for triggering the function.

## Usage

After deployment, you can use the function as follows:

```bash
curl -X POST https://YOUR_FUNCTION_URL \
-H "Content-Type: application/json" \
-d '{"search_term": "your search query"}'
```

Replace `YOUR_FUNCTION_URL` with the URL of your deployed function, and fill in
the search query.

If you run into problems, go to
[Google Cloud Functions](https://console.cloud.google.com/functions), find the
function you just deployed, and review the logs for informative errors. Perhaps
you need to setup
[Google Cloud IAM](https://cloud.google.com/functions/docs/reference/iam) roles
or permissions.

## Customization

This implementation provides a basic way to access and control your queries to
the Vertex AI Search API. It simplifies CORS and bearer token authentication,
and allows for some minor customization of inputs and outputs.

If you require more extensive customization, consider using an orchestration
framework like [LangChain](https://www.langchain.com/) or
[LlamaIndex](https://www.llamaindex.ai/) which have Vertex AI Search
integrations.
