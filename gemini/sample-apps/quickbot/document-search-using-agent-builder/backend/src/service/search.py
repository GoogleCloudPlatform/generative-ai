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

"""Service for performing searches using Google Cloud Discovery Engine."""

from google.cloud.discoveryengine_v1 import SearchRequest, SearchServiceClient
from src.model.search import (
    SearchApplication,
    SearchResult,
    SearchResultsWithSummary,
)

CONTENT_SEARCH_SPEC = SearchRequest.ContentSearchSpec(
    snippet_spec=SearchRequest.ContentSearchSpec.SnippetSpec(
        return_snippet=True
    ),
    extractive_content_spec=SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
        max_extractive_answer_count=1
    ),
    summary_spec=SearchRequest.ContentSearchSpec.SummarySpec(
        summary_result_count=5,
        include_citations=True,
        ignore_adversarial_query=True,
        ignore_non_summary_seeking_query=True,
        model_spec=SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
            version="stable",
        ),
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
    Handles search operations using a configured
    Discovery Engine Search Application.

    Initializes with a specific SearchApplication configuration and provides
    methods to perform searches against the corresponding engine.
    """

    def __init__(self, search_application: SearchApplication):
        """
        Initializes the SearchService.

        Args:
            search_application: The configuration object defining the target
                                search engine, location, and serving config.
        """
        self.search_client = SearchServiceClient(
            client_options=search_application.get_client_options()
        )
        self.serving_config = search_application.get_serving_config()

    def search(self, term: str) -> SearchResultsWithSummary:
        """
        Performs a search against the configured Discovery Engine.

        Constructs a search request with predefined content specifications,
        query expansion, and spell correction settings. Parses the response
        to extract results, snippets, links, and a summary.

        Args:
            term: The search query string.

        Returns:
            A SearchResultsWithSummary object containing the search summary
            and a list of SearchResult objects. Returns an empty list of
            results and a default summary message if the search fails or
            yields no results.

        Raises:
            Logs errors if the API call fails.
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

        summary_text = (
            data.summary.summary_text
            if data.summary and data.summary.summary_text
            else "No summary available"
        )

        # Process results
        for r in data.results:
            document = r.document
            derived_data = document.derived_struct_data
            gcs_link = derived_data.get("link").replace(
                "gs://", "https://storage.cloud.google.com/"
            )

            # Extract snippet safely
            snippets = derived_data.get("snippets", [])
            snippet_text = (
                snippets[0].get("snippet", "No snippet available")
                if snippets
                else "No snippet available"
            )
            extractive_answers = derived_data.get("extractive_answers", [])
            content_text = (
                extractive_answers[0].get("content", "No content available")
                if extractive_answers
                else "No content available"
            )
            # Map to SearchResult
            mapped_result = SearchResult(
                document_id=document.id,
                title=derived_data.get("title", "Untitled"),
                snippet=snippet_text,
                link=gcs_link,
                content=content_text,
            )
            results.append(mapped_result)

        response_result = SearchResultsWithSummary(
            summary=summary_text, results=results
        )

        return response_result
