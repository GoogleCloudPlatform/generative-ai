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
the Vertex AI Search API. It uses the VertexAISearchClient to handle
the core search functionality.

For deployment instructions, environment variable setup, and usage examples,
please refer to the README.md file.
"""

import os
from typing import Any, Dict, Tuple

from flask import Flask, Request, jsonify, request
import functions_framework
from google.api_core.exceptions import GoogleAPICallError
from vertex_ai_search_client import VertexAISearchClient, VertexAISearchConfig

# Load environment variables
project_id = os.getenv("PROJECT_ID", "your-project")
location = os.getenv("LOCATION", "global")
data_store_id = os.getenv("DATA_STORE_ID", "your-data-store")
engine_data_type = os.getenv("ENGINE_DATA_TYPE", "UNSTRUCTURED")
engine_chunk_type = os.getenv("ENGINE_CHUNK_TYPE", "CHUNK")
summary_type = os.getenv("SUMMARY_TYPE", "VERTEX_AI_SEARCH")

# Create VertexAISearchConfig
config = VertexAISearchConfig(
    project_id=project_id,
    location=location,
    data_store_id=data_store_id,
    engine_data_type=engine_data_type,
    engine_chunk_type=engine_chunk_type,
    summary_type=summary_type,
)

# Initialize VertexAISearchClient
vertex_ai_search_client = VertexAISearchClient(config)


@functions_framework.http
def vertex_ai_search(http_request: Request) -> Tuple[Any, int, Dict[str, str]]:
    """
    Handle HTTP requests for Vertex AI Search.

    This function processes incoming HTTP requests, performs the search using
    the VertexAISearchClient, and returns the results. It handles CORS, validates
    the request, and manages potential errors.

    Args:
        http_request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        Tuple[Any, int, Dict[str, str]]: A tuple containing the response body,
        status code, and headers. This output will be turned into a Response
        object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    # Set CORS headers for the preflight request
    if http_request.method == "OPTIONS":
        # Allows GET requests from any origin with the Content-Type
        # header and caches preflight response for an 3600s
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }
        return ("", 204, headers)

    # Set CORS headers for all responses
    headers = {"Access-Control-Allow-Origin": "*"}

    def create_error_response(
        message: str, status_code: int
    ) -> Tuple[Any, int, Dict[str, str]]:
        """Standardize the error responses with common headers."""
        return (jsonify({"error": message}), status_code, headers)

    # Handle the request and get the search_term
    request_json = http_request.get_json(silent=True)
    request_args = http_request.args

    if request_json and "search_term" in request_json:
        search_term = request_json["search_term"]
    elif request_args and "search_term" in request_args:
        search_term = request_args["search_term"]
    else:
        return create_error_response("No search term provided", 400)

    # Handle the Vertex AI Search and return JSON
    try:
        results = vertex_ai_search_client.search(search_term)
        return (jsonify(results), 200, headers)
    except GoogleAPICallError as e:
        return create_error_response(
            f"Error calling Vertex AI Search API: {str(e)}", 500
        )
    except ValueError as e:
        return create_error_response(f"Invalid input: {str(e)}", 400)


if __name__ == "__main__":
    app = Flask(__name__)

    @app.route("/", methods=["POST"])
    def index() -> Tuple[Any, int, Dict[str, str]]:
        """
        Flask route for handling POST requests when running locally.

        This function is used when the script is run directly (not as a Google Cloud Function).
        It mimics the behavior of the vertex_ai_search function for local testing.

        Returns:
            Tuple[Any, int, Dict[str, str]]: The vertex search result.
        """

        return vertex_ai_search(request)

    app.run("localhost", 8080, debug=True)
