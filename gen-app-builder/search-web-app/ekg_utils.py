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

"""Enterprise Knowledge Graph Utilities"""
import json
from typing import List, Optional, Sequence, Tuple

from google.cloud import enterpriseknowledgegraph as ekg

JSON_INDENT = 2


# pylint: disable=too-many-arguments
def search_public_kg(
    project_id: str,
    location: str,
    search_query: str,
    languages: Optional[Sequence[str]] = None,
    types: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
) -> Tuple:
    """
    Make API Request to Public Knowledge Graph.
    """
    client = ekg.EnterpriseKnowledgeGraphServiceClient()

    # Fully qualified location string, e.g. projects/{project_id}/locations/{location}
    parent = client.common_location_path(project=project_id, location=location)

    request = ekg.SearchPublicKgRequest(
        parent=parent, query=search_query, languages=languages, types=types, limit=limit
    )

    response = client.search_public_kg(request=request)

    request_url = f"https://enterpriseknowledgegraph.googleapis.com/v1/{parent}/publicKnowledgeGraphEntities:Search?query={search_query}"  # noqa: E501

    request_json = ekg.SearchPublicKgRequest.to_json(
        request, including_default_value_fields=False, indent=JSON_INDENT
    )

    response_json = ekg.SearchPublicKgResponse.to_json(
        response, including_default_value_fields=False, indent=JSON_INDENT
    )

    entities = get_entities(response)
    return entities, request_url, request_json, response_json


def get_entities(response: ekg.SearchPublicKgResponse) -> List:
    """
    Extract Entitities from Knowledge Graph Response
    """
    item_list_element = ekg.SearchPublicKgResponse.to_dict(response)[
        "item_list_element"
    ]

    entities = []
    for element in item_list_element:
        result = element["result"]
        result["resultJson"] = json.dumps(result, sort_keys=True, indent=JSON_INDENT)
        entities.append(result)

    return entities
