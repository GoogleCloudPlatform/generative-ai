# Copyright 2023 Google LLC
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

"""Example Google Cloud Function serving Vertex AI Search

This is an optional interface between Vertex AI Search API, showing how you
might create your own Google Cloud Function as a proxy.  You may do this to
simplify CORS and bearer token authentication, or to customize and intercept
certain inputs and outputs.

If you want more customization, you may want to use an orchestration platform
like LangChain, PromptFlow, Breadboard, etc.
"""

import html
import json
import re

# https://cloud.google.com/functions/docs/samples/functions-http-content
import functions_framework
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1alpha as discoveryengine
from proto import Message

# Use Vertex AI Search API to find relevant docs for searches & sumamrize them.
# https://cloud.google.com/python/docs/reference/discoveryengine/latest
# https://cloud.google.com/generative-ai-app-builder/docs/libraries

# Your Vertex AI Search config
project_id = "ENTER_YOUR_PROJECT_NAME_HERE"  # alphanumeric
location = "global"  # or an alternate location
data_store_id = "ENTER_YOUR_DATA_STORE_ID_HERE"  # not the app id, alphanumeric


def get_document_info(search_result_dict):
    """Extracts metadata from a Data Store Results document."""
    # https://cloud.google.com/generative-ai-app-builder/docs/reference/rest/v1alpha/SearchResponse
    document = search_result_dict.get("document", {})
    # Optional medatadata you may have set when creating your data store.
    # https://cloud.google.com/generative-ai-app-builder/docs/prepare-data
    struct_data = document.get("struct_data", {})
    # Standard derived metadata
    derived_struct_data = document.get("derived_struct_data", {})
    extractive_answers = derived_struct_data.get("extractive_answers", {})
    description = extractive_answers[0].get("content") if extractive_answers else None
    return {
        "id": document.get("id"),
        "metadata": {
            "url": struct_data.get("url"),
            "title": struct_data.get("title"),
            "tags": struct_data.get("tags"),
            "keywords": struct_data.get("keywords"),
            "description": description,
        },
        "link": struct_data.get("url", derived_struct_data.get("link")),
        "doc_link": derived_struct_data.get("link"),
        "snippets": [
            snippet.get("snippet")
            for snippet in derived_struct_data.get("snippets")
            if snippet.get("snippet_status") == "SUCCESS"
        ],
    }


def query_vertex_search_api_for_term(search_query):
    """Performs Vertex AI Search for search_query."""
    # https://cloud.google.com/generative-ai-app-builder/docs/locations#specify_a_multi-region_for_your_data_store
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )
    # Create a client
    client = discoveryengine.SearchServiceClient(client_options=client_options)

    # The full resource name of the search engine serving config
    # e.g. projects/{project_id}/locations/{location}/dataStores/{data_store_id}/servingConfigs/{serving_config_id}
    serving_config = client.serving_config_path(
        project=project_id,
        location=location,
        data_store=data_store_id,
        serving_config="default_config",
    )

    # Optional: Configuration options for search
    # Refer to the `ContentSearchSpec` reference for all supported fields:
    # https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchRequest.ContentSearchSpec
    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        # For information about snippets, refer to:
        # https://cloud.google.com/generative-ai-app-builder/docs/snippets
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True
        ),
        extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
            max_extractive_answer_count=1
        ),
        # For information about search summaries, refer to:
        # https://cloud.google.com/generative-ai-app-builder/docs/get-search-summaries
        summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
            summary_result_count=5,
            include_citations=True,
            ignore_adversarial_query=True,
            ignore_non_summary_seeking_query=True,
        ),
    )

    # Refer to the `SearchRequest` reference for all supported fields:
    # https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchRequest
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=search_query,
        page_size=10,
        content_search_spec=content_search_spec,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
        ),
    )

    # Execute the search and return the response as proto.
    response = client.search(request)
    # Get the documents as a simple dict for JSON response.
    documents = [
        get_document_info(Message.to_dict(result)) for result in response.results
    ]

    output = {
        "summary": response.summary.summary_text,
        "total_size": response.total_size,
        "attribution_token": response.attribution_token,
        "next_page_token": response.next_page_token,
        "documents": documents,
    }
    return json.dumps(output)


@functions_framework.http
def vertex_search(request):
    """HTTP Cloud Function.

    Args:
        request (flask.Request): The request object.
          <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    # Set CORS headers for the preflight request
    if request.method == "OPTIONS":
        # Allows GET requests from any origin with the Content-Type
        # header and caches preflight response for an 3600s
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }

        return ("", 204, headers)

    # Set CORS headers for the main request
    headers = {"Access-Control-Allow-Origin": "*"}

    # Handle a variety of inputs types and params.
    if isinstance(request, str):
        search_term = request
    else:
        if "content-type" not in request.headers:
            return ("Please specify a 'content-type' header", 422, headers)

        content_type = request.headers["content-type"]
        if "application/json" in content_type:
            request_json = request.get_json(silent=True)
            if request_json and "search_term" in request_json:
                search_term = request_json["search_term"]
            else:
                return (
                    "JSON is invalid, or missing a 'search_term' property",
                    422,
                    headers,
                )
        elif "application/octet-stream" in content_type:
            search_term = request.data
        elif "text/plain" in content_type:
            search_term = request.data
        elif "application/x-www-form-urlencoded" in content_type:
            search_term = request.form.get("search_term")
        else:
            return (f"Unknown content type: {content_type}", 422, headers)

    results = query_vertex_search_api_for_term(search_term)

    # Remove HTML and URL formatting from response.
    results = re.sub("<.*?>", "", results)
    results = html.unescape(results)

    return (results, 200, headers)
