# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Google Cloud Function for Vertex AI Search

This module provides an HTTP endpoint for performing searches using
the Vertex AI Search API. It uses the VertexSearchClient to handle
the core search functionality.

This is an optional means to access and control your queries to the
Vertex AI Search API. You may do this to simplify CORS and bearer
token authentication, or to customize inputs and outputs.

If you want more customization, you may want to use an orchestration
framework like LangChain, PromptFlow, Breadboard, etc.

To deploy this function:
1. Ensure you have the Google Cloud SDK installed and configured.
2. Run: gcloud functions deploy vertex_search --runtime python39 --trigger-http --allow-unauthenticated

Environment variables required:
- PROJECT_ID: Your Google Cloud project ID
- LOCATION: The location of your Vertex AI Search data store
- DATA_STORE_ID: The ID of your Vertex AI Search data store
- ENGINE_DATA_TYPE: Type of data in the engine (0-3)
- ENGINE_CHUNK_TYPE: Type of chunking used (0-3)
- SUMMARY_TYPE: Type of summary used (0-3)

Example usage (after deployment):
    curl -X POST https://YOUR_FUNCTION_URL \
    -H "Content-Type: application/json" \
    -d '{"search_term": "your search query"}'

See the README.md for more options including local development.

"""

import os
import json
import functions_framework
from vertex_search_client import VertexSearchClient
from google.api_core.exceptions import GoogleAPICallError

# Initialize the VertexSearchClient
client = VertexSearchClient(
    project_id=os.getenv("PROJECT_ID"),
    location=os.getenv("LOCATION"),
    data_store_id=os.getenv("DATA_STORE_ID"),
    engine_data_type=os.getenv("ENGINE_DATA_TYPE", 0),
    engine_chunk_type=os.getenv("ENGINE_CHUNK_TYPE", 1),
    summary_type=os.getenv("SUMMARY_TYPE", 1),
)


def set_cors_headers(headers):
    headers.update(
        {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }
    )


@functions_framework.http
def vertex_search(request):
    headers = {}
    set_cors_headers(headers)

    if request.method == "OPTIONS":
        return ("", 204, headers)

    if request.content_type != "application/json":
        return ("Please send a JSON request", 415, headers)

    request_json = request.get_json(silent=True)
    if not request_json or "search_term" not in request_json:
        return ("Invalid JSON, missing 'search_term' field", 400, headers)

    try:
        results = client.search(request_json["search_term"])
        return (json.dumps(results, indent=2), 200, headers)
    except GoogleAPICallError as e:
        return (f"Error calling Vertex AI Search API: {str(e)}", 500, headers)
    except json.JSONDecodeError as e:
        return (f"Error parsing search results: {str(e)}", 500, headers)
    except Exception as e:
        return (f"Unexpected error: {str(e)}", 500, headers)


if __name__ == "__main__":
    from flask import Flask, request

    app = Flask(__name__)

    @app.route("/", methods=["POST"])
    def index():
        return vertex_search(request)

    app.run("localhost", 8080, debug=True)
