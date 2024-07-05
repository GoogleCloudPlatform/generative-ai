# Vertex AI Search accessed via Google Cloud Functions

This example is based on a Google Cloud Function using a HTTPS trigger on a
Python 3 runtime;
[read more here](https://cloud.google.com/functions/docs/samples/functions-http-content#functions_http_content-python).

This example is based on the
[Python client for the Vertex AI Search API](https://cloud.google.com/generative-ai-app-builder/docs/libraries#client-libraries-usage-python),
which will get search results, snippets, metadata, and the LLM
summary grounded on search results.

**[Read more about Vertex AI Search accessed via Google Cloud Functions](../README.md)**

## Run locally

Run this code locally via **Functions Framework** or **Functions Emulator**;
[read more about running cloud functions locally](https://cloud.google.com/functions/docs/running/overview).

NOTE: this uses a `.env` file to manage local environment values.  You can
optionally use the `setup_env.sh` script to setup or you can manually edit it.

```bash
gcloud auth login
bash setup_env.sh
pip install -r requirements.txt
pip install functions-framework
functions-framework --target=vertex_search
```

In a different terminal, execute a `POST` search query based on your data.

```bash
export SEARCH_TERM="Does Cymbal Bank offer a HSA and what are the monthly premiums in the US?"
curl -m 310 -X POST localhost:8080 \
-H "Content-Type: application/json" \
-d "{\"search_term\": \"${SEARCH_TERM}\"}"
```
