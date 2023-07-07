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
from os.path import basename
from typing import List, Optional, Tuple

from google.cloud import discoveryengine, discoveryengine_v1beta

JSON_INDENT = 2


def list_documents(
    project_id: str,
    location: str,
    datastore_id: str,
) -> List[discoveryengine.Document]:
    client = discoveryengine.DocumentServiceClient()

    parent = client.branch_path(
        project=project_id,
        location=location,
        data_store=datastore_id,
        branch="default_branch",
    )

    request = discoveryengine.ListDocumentsRequest(parent=parent, page_size=10)

    page_result = client.list_documents(request=request)

    return [
        {"id": document.id, "title": basename(document.content.uri)}
        for document in page_result
    ]


def search_enterprise_search(
    project_id: str,
    location: str,
    search_engine_id: str,
    search_query: str,
) -> Tuple:
    # Create a client
    client = discoveryengine.SearchServiceClient()

    # The full resource name of the search engine serving config
    # e.g. projects/{project_id}/locations/{location}
    serving_config = client.serving_config_path(
        project=project_id,
        location=location,
        data_store=search_engine_id,
        serving_config="default_config",
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config, query=search_query, page_size=50
    )
    response_pager = client.search(request)

    response = discoveryengine.SearchResponse(
        results=response_pager.results,
        facets=response_pager.facets,
        guided_search_result=response_pager.guided_search_result,
        total_size=response_pager.total_size,
        attribution_token=response_pager.attribution_token,
        next_page_token=response_pager.next_page_token,
        corrected_query=response_pager.corrected_query,
        summary=response_pager.summary,
    )

    request_url = f"https://discoveryengine.googleapis.com/v1/{serving_config}:search"

    request_json = discoveryengine.SearchRequest.to_json(
        request, including_default_value_fields=True, indent=JSON_INDENT
    )
    response_json = discoveryengine.SearchResponse.to_json(
        response, including_default_value_fields=False, indent=JSON_INDENT
    )

    results = get_enterprise_search_results(response)
    return results, request_url, request_json, response_json


def get_enterprise_search_results(response: discoveryengine.SearchResponse) -> List:
    """
    Extract Results from Enterprise Search Response
    """

    results = []
    for result in response.results:
        data = result.document.derived_struct_data

        cse_thumbnail = data["pagemap"].get("cse_thumbnail")
        if cse_thumbnail:
            image = cse_thumbnail[0]["src"]
        else:
            image = "https://www.google.com/images/errors/robot.png"
        results.append(
            {
                "title": data["title"],
                "htmlTitle": data["htmlTitle"],
                "link": data["link"],
                "htmlFormattedUrl": data["htmlFormattedUrl"],
                "displayLink": data["displayLink"],
                "snippets": [s["htmlSnippet"] for s in data["snippets"]],
                "thumbnailImage": image,
                "resultJson": discoveryengine.SearchResponse.SearchResult.to_json(
                    result, including_default_value_fields=True, indent=JSON_INDENT
                ),
            }
        )

    return results


def recommend_personalize(
    project_id: str,
    location: str,
    datastore_id: str,
    serving_config_id: str,
    document_id: str,
    user_pseudo_id: Optional[str] = "xxxxxxxxxxx",
    attribution_token: Optional[str] = None,
) -> Tuple:
    # Create a client
    client = discoveryengine_v1beta.RecommendationServiceClient()

    # The full resource name of the search engine serving config
    # e.g. projects/{project_id}/locations/{location}
    serving_config = client.serving_config_path(
        project=project_id,
        location=location,
        data_store=datastore_id,
        serving_config=serving_config_id,
    )

    user_event = discoveryengine_v1beta.UserEvent(
        event_type="view-item",
        user_pseudo_id=user_pseudo_id,
        attribution_token=attribution_token,
        documents=[discoveryengine_v1beta.DocumentInfo(id=document_id)],
    )

    request = discoveryengine_v1beta.RecommendRequest(
        serving_config=serving_config,
        user_event=user_event,
        params={"returnDocument": True, "returnScore": True},
    )

    response = client.recommend(request)

    request_url = (
        f"https://discoveryengine.googleapis.com/v1beta/{serving_config}:recommend"
    )

    request_json = discoveryengine_v1beta.RecommendRequest.to_json(
        request, including_default_value_fields=True, indent=JSON_INDENT
    )
    response_json = discoveryengine_v1beta.RecommendResponse.to_json(
        response, including_default_value_fields=False, indent=JSON_INDENT
    )

    results = get_personalize_results(response)
    return results, response.attribution_token, request_url, request_json, response_json


def get_personalize_results(response: discoveryengine_v1beta.RecommendResponse) -> List:
    """
    Extract Results from Personalize Response
    """

    results = []
    for result in response.results:
        results.append(
            {
                "id": result.id,
                "title": basename(result.document.content.uri),
                "htmlFormattedUrl": result.document.content.uri,
                "link": result.document.content.uri.replace(
                    "gs://", "https://storage.googleapis.com/"
                ),
                "mimeType": result.document.content.mime_type,
                "resultJson": discoveryengine_v1beta.RecommendResponse.RecommendationResult.to_json(
                    result, including_default_value_fields=True, indent=JSON_INDENT
                ),
            }
        )

    return results
