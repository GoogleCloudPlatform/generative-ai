# Copyright 2022 Google LLC
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

"""Generative AI App Builder Utilities"""
import json
from typing import List, Sequence, Tuple

from google.cloud import discoveryengine_v1beta as genappbuilder

JSON_INDENT = 2


def search_enterprise_search(
    project_id: str,
    location: str,
    search_engine_id: str,
    search_query: str,
) -> Tuple:
    # Create a client
    client = genappbuilder.SearchServiceClient()

    # The full resource name of the search engine serving config
    # e.g. projects/{project_id}/locations/{location}
    serving_config = client.serving_config_path(
        project=project_id,
        location=location,
        data_store=search_engine_id,
        serving_config="default_config",
    )

    request = genappbuilder.SearchRequest(
        serving_config=serving_config, query=search_query, page_size=50
    )
    response_pager = client.search(request)

    response = genappbuilder.SearchResponse(
        results=response_pager.results,
        facets=response_pager.facets,
        guided_search_result=response_pager.guided_search_result,
        total_size=response_pager.total_size,
        attribution_token=response_pager.attribution_token,
        next_page_token=response_pager.next_page_token,
        corrected_query=response_pager.corrected_query,
        summary=response_pager.summary,
    )

    request_url = (
        f"https://discoveryengine.googleapis.com/v1beta/{serving_config}:search"
    )

    request_json = genappbuilder.SearchRequest.to_json(
        request, including_default_value_fields=True, indent=JSON_INDENT
    )
    response_json = genappbuilder.SearchResponse.to_json(
        response, including_default_value_fields=False, indent=JSON_INDENT
    )

    results = get_results(response)
    return results, request_url, request_json, response_json


def get_results(response: genappbuilder.SearchResponse) -> List:
    """
    Extract Results from Enterprise Search Response
    """

    results = []
    for result in response.results:
        data = result.document.derived_struct_data
        results.append(
            {
                "title": data["title"],
                "htmlTitle": data["htmlTitle"],
                "formattedUrl": data["formattedUrl"],
                "htmlFormattedUrl": data["htmlFormattedUrl"],
                "displayLink": data["displayLink"],
                "snippets": [s["htmlSnippet"] for s in data["snippets"]],
                "thumbnailImage": data["pagemap"]["cse_thumbnail"][0]["src"],
                "resultJson": genappbuilder.SearchResponse.SearchResult.to_json(
                    result, including_default_value_fields=True, indent=JSON_INDENT
                ),
            }
        )

    return results
