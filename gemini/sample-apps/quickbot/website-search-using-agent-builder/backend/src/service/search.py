# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Service layer for interacting with the Google Cloud Discovery Engine Search API.

This module provides the SearchService class, which encapsulates the logic for
constructing search requests, executing them against a configured 
Discovery Engine, and processing the results into a standardized format.
"""

from typing import List
from google.cloud.discoveryengine_v1 import SearchRequest, SearchServiceClient
from src.model.search import SearchApplication, SearchResult

CONTENT_SEARCH_SPEC = SearchRequest.ContentSearchSpec(
    snippet_spec=SearchRequest.ContentSearchSpec.SnippetSpec(
        return_snippet=True
    ),
    extractive_content_spec=SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
        max_extractive_answer_count=1
    ),
)
QUERY_EXPANSION_SPEC = SearchRequest.QueryExpansionSpec(
    condition=SearchRequest.QueryExpansionSpec.Condition.AUTO,
)
SPELL_CORRECTION_SPEC = SearchRequest.SpellCorrectionSpec(
    mode=SearchRequest.SpellCorrectionSpec.Mode.AUTO
)


class SearchService:
    """
    Handles search operations using Google Cloud Discovery Engine.

    This service takes a SearchApplication configuration, initializes the
    necessary Discovery Engine client, and provides a method to perform
    searches based on a given term.
    """

    def __init__(self, search_application: SearchApplication):
        """
        Initializes the SearchService.

        Sets up the Discovery Engine SearchServiceClient with appropriate
        client options based on the region specified in the search_application.
        It also stores the serving configuration path derived from the
        search_application details.

        Args:
            search_application: The SearchApplication configuration containing
                                engine ID, region, and other necessary details
                                to connect to the correct Discovery Engine.
        """
        self.search_client = SearchServiceClient(
            client_options=search_application.get_client_options()
        )
        self.serving_config = search_application.get_serving_config()

    def search(self, term: str) -> List[SearchResult]:
        """
        Performs a search query against the configured Discovery Engine.

        Constructs a SearchRequest with the provided search term and predefined
        configs for content search, query expansion and spell correction.
        It then calls the Discovery Engine API, processes the results, filters
        them (currently only keeping 'en' locale results), extracts relevant
        information like title, snippet, link, and image, and maps them to
        SearchResult objects.

        Args:
            term: The search query string entered by the user.

        Returns:
            A list of SearchResult objects representing the processed and
            filtered search results. Returns an empty list if no relevant
            results are found or if an error occurs during the API call
            (though errors are not explicitly handled here beyond the client).
        """
        request = SearchRequest(
            serving_config=self.serving_config,
            query=term,
            page_size=10,
            content_search_spec=CONTENT_SEARCH_SPEC,
            query_expansion_spec=QUERY_EXPANSION_SPEC,
            spell_correction_spec=SPELL_CORRECTION_SPEC,
        )

        data = self.search_client.search(request)
        results = []

        # Process results
        for r in data.results:
            document = r.document
            derived_data = document.derived_struct_data
            if (
                derived_data.get("pagemap").get("metatags")[0].get("og:locale")
                != "en"
            ):
                continue

            # Extract snippet safely
            snippets = derived_data.get("snippets")
            snippet_text = (
                snippets[0].get("snippet", "No snippet available")
                if snippets
                else "No snippet available"
            )

            # Map to SearchResult
            mapped_result = SearchResult(
                document_id=document.id,
                title=derived_data.get("title", "Untitled"),
                snippet=snippet_text,
                link=derived_data.get("link"),
                formatted_url=derived_data.get("formattedUrl"),
                img=derived_data.get("pagemap")
                .get("cse_thumbnail")[0]
                .get("src"),
                displayLink=derived_data.get("displayLink"),
            )
            results.append(mapped_result)

        return results
