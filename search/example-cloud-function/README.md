# Example of a Google Cloud Function serving Vertex AI Search results

[Cloud functions](https://cloud.google.com/functions/) supports many triggers and runtimes.

This example is based on a HTTPS trigger on a Python 3 runtime:
https://cloud.google.com/functions/docs/samples/functions-http-content#functions_http_content-python

[Vertex AI Search](https://cloud.google.com/generative-ai-app-builder/) exposes a search (and summary) API.

This example is based on the Python client for the Vertex AI Search API endpoint, which will get search results, snippets, metadata, and the LLM summary grounded on search results:
https://cloud.google.com/generative-ai-app-builder/docs/libraries#client-libraries-usage-python

```miranda
flowchart LR
    A[Vertex Search AI] --> B(Google Cloud Function)
    B --> C[My App Server]
    C -->|One| D[fa:fa-laptop web]
    C -->|Two| E[fa:fa-mobile mobile]
```

