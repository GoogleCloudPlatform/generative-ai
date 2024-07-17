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

For deployment instructions, environment variable setup, and usage examples,
please refer to the README.md file.
"""

import json
import os
from typing import Dict, Tuple

from flask import Request
import functions_framework
from google.api_core.exceptions import GoogleAPICallError
from vertex_search_client import VertexSearchClient

# Initialize the VertexSearchClient
client = VertexSearchClient(
    project_id=os.getenv("PROJECT_ID", "your-project"),
    location=os.getenv("LOCATION", "global"),
    data_store_id=os.getenv("DATA_STORE_ID", "your-data-store"),
    engine_data_type=os.getenv("ENGINE_DATA_TYPE", "UNSTRUCTURED"),
    engine_chunk_type=os.getenv("ENGINE_CHUNK_TYPE", "CHUNK"),
    summary_type=os.getenv("SUMMARY_TYPE", "VERTEX_AI_SEARCH"),
)


def set_cors_headers(headers: Dict[str, str]) -> None:
    """
    Set CORS headers for the response.

    This function adds the necessary headers to allow cross-origin requests.

    Args:
        headers (Dict[str, str]): The headers dictionary to update with CORS headers.
    """
    headers.update(
        {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }
    )


@functions_framework.http
def vertex_search(request: Request) -> Tuple[str, int, Dict[str, str]]:
    """
    Handle HTTP requests for Vertex AI Search.

    This function processes incoming HTTP requests, performs the search using
    the VertexSearchClient, and returns the results. It handles CORS, validates
    the request, and manages potential errors.

    Args:
        request (flask.Request): The incoming HTTP request object.

    Returns:
        Tuple[str, int, Dict[str, str]]: A tuple containing the response body,
        status code, and headers.
    """
    headers: Dict[str, str] = {}
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
    from flask import Flask

    app = Flask(__name__)

    @app.route("/", methods=["POST"])
    def index() -> Tuple[str, int, Dict[str, str]]:
        """
        Flask route for handling POST requests when running locally.

        This function is used when the script is run directly (not as a Google Cloud Function).
        It mimics the behavior of the vertex_search function for local testing.

        Returns:
            Tuple[str, int, Dict[str, str]]: The result of calling vertex_search with the current request.
        """
        return vertex_search(request)

    app.run("localhost", 8080, debug=True)
