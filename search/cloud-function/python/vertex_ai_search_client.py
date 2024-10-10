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
VertexAISearchClient for interacting with Google Cloud Vertex AI Search.

This module provides a client class for simplifying interactions with the
Vertex AI Search API. It handles configuration, query construction, and
result parsing.

Example usage:
    config = VertexAISearchConfig(
        project_id="your-project",
        location="global",
        data_store_id="your-data-store",
        engine_data_type="UNSTRUCTURED",
        engine_chunk_type="CHUNK",
        summary_type="VERTEX_AI_SEARCH",
    )
    client = VertexAISearchClient(config)
    results = client.search("your search query")
    print(results)
"""
from dataclasses import dataclass
import html
import json
import re
from typing import Any, Literal

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1alpha as discoveryengine
from google.cloud.discoveryengine_v1alpha.services.search_service.pagers import (
    SearchPager,
)
from google.cloud.discoveryengine_v1alpha.types import SearchResponse

# Define types using string literals, similar to enums.
EngineDataTypeStr = Literal["UNSTRUCTURED", "STRUCTURED", "WEBSITE", "BLENDED"]
EngineChunkTypeStr = Literal[
    "DOCUMENT_WITH_SNIPPETS", "DOCUMENT_WITH_EXTRACTIVE_SEGMENTS", "CHUNK"
]
SummaryTypeStr = Literal[
    "NONE", "VERTEX_AI_SEARCH", "GENERATE_GROUNDED_ANSWERS", "GEMINI"
]


@dataclass
class VertexAISearchConfig:
    """Config for the Vertex AI Search data store."""

    project_id: str
    location: str
    data_store_id: str
    engine_data_type: EngineDataTypeStr | str
    engine_chunk_type: EngineChunkTypeStr | str
    summary_type: SummaryTypeStr | str

    def __post_init__(self) -> None:
        """Validate and convert string inputs to appropriate types."""
        self.engine_data_type = self._validate_enum(
            self.engine_data_type, EngineDataTypeStr, "UNSTRUCTURED"
        )
        self.engine_chunk_type = self._validate_enum(
            self.engine_chunk_type, EngineChunkTypeStr, "CHUNK"
        )
        self.summary_type = self._validate_enum(
            self.summary_type, SummaryTypeStr, "VERTEX_AI_SEARCH"
        )

    @staticmethod
    def _validate_enum(value: str, enum_type: Any, default: str) -> str:
        """Validate and convert string to enum type."""
        if value in enum_type.__args__:
            return value
        print(f"Warning: Invalid value '{value}'. Using default: '{default}'")
        return default

    def to_dict(self) -> dict[str, str]:
        """Convert the config to a dictionary."""
        return {
            "project_id": self.project_id,
            "location": self.location,
            "data_store_id": self.data_store_id,
            "engine_data_type": self.engine_data_type,
            "engine_chunk_type": self.engine_chunk_type,
            "summary_type": self.summary_type,
        }


class VertexAISearchClient:
    """
    A client for interacting with Google Cloud Vertex AI Search.

    This class provides methods to configure the search engine, perform searches,
    and parse the results. It supports different types of data stores and search
    configurations.
    """

    def __init__(self, config: VertexAISearchConfig):
        """
        Initialize the VertexAISearchClient.

        Args:
            config (VertexAISearchConfig): The configuration for the Vertex AI Search client.
        """
        self.config = config
        self.client = self._create_client()
        self.serving_config = self._get_serving_config()

    def _create_client(self) -> discoveryengine.SearchServiceClient:
        """
        Create and configure the SearchServiceClient.

        Returns:
            discoveryengine.SearchServiceClient: The configured client.
        """
        client_options = None
        if self.config.location != "global":
            api_endpoint = f"{self.config.location}-discoveryengine.googleapis.com"
            client_options = ClientOptions(api_endpoint=api_endpoint)
        return discoveryengine.SearchServiceClient(client_options=client_options)

    def _get_serving_config(self) -> str:
        """
        Get the serving configuration path for the Vertex AI Search data store.

        Returns:
            str: The serving configuration path.
        """
        return self.client.serving_config_path(
            project=self.config.project_id,
            location=self.config.location,
            data_store=self.config.data_store_id,
            serving_config="default_config",
        )

    def search(self, query: str, page_size: int = 10) -> dict[str, Any]:
        """
        Perform a search query using Vertex AI Search.

        Args:
            query (str): The search query.
            page_size (int): Number of results to return per page.

        Returns:
            dict: Parsed and simplified search results.
        """
        request = self.build_search_request(query, page_size)
        print(f"<request> {request} </request>")
        search_pager = self.client.search(request)
        response = self.map_search_pager_to_dict(search_pager)
        print(f"<response> {response} </response>")
        return self.simplify_search_results(response)

    def build_search_request(
        self, query: str, page_size: int
    ) -> discoveryengine.SearchRequest:
        """
        Build a SearchRequest object based on the client configuration and query.

        Args:
            query (str): The search query.
            page_size (int): Number of results to return per page.

        Returns:
            discoveryengine.SearchRequest: The configured search request object.
        """
        snippet_spec = None
        extractive_content_spec = None
        if self.config.engine_chunk_type == "DOCUMENT_WITH_SNIPPETS":
            snippet_spec = discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                return_snippet=True,
            )
        if self.config.engine_chunk_type == "DOCUMENT_WITH_EXTRACTIVE_SEGMENTS":
            snippet_spec = discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                return_snippet=True,
            )
            extractive_content_spec = (
                discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                    max_extractive_answer_count=1,
                    return_extractive_segment_score=True,
                )
            )

        summary_spec = None
        if self.config.summary_type == "VERTEX_AI_SEARCH":
            summary_spec = discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                summary_result_count=5,
                include_citations=True,
                ignore_adversarial_query=True,
                ignore_non_summary_seeking_query=True,
            )

        return discoveryengine.SearchRequest(
            serving_config=self.serving_config,
            query=query,
            page_size=page_size,
            content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                snippet_spec=snippet_spec,
                extractive_content_spec=extractive_content_spec,
                summary_spec=summary_spec,
            ),
            query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
                condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
            ),
            spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            ),
        )

    def map_search_pager_to_dict(self, pager: SearchPager) -> dict[str, Any]:
        """
        Maps a SearchPager to a dictionary structure, iterativly requesting results.

        https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1alpha.services.search_service.pagers.SearchPager

        Args:
            pager (SearchPager): The pager returned by the search method.

        Returns:
            Dict[str, Any]: A dictionary containing the search results and metadata.
        """
        output: dict[str, Any] = {
            "results": [
                SearchResponse.SearchResult.to_dict(result) for result in pager
            ],
            "total_size": pager.total_size,
            "attribution_token": pager.attribution_token,
            "next_page_token": pager.next_page_token,
            "corrected_query": pager.corrected_query,
            "facets": [],
            "applied_controls": [],
        }

        if pager.summary:
            output["summary"] = SearchResponse.Summary.to_dict(pager.summary)

        if pager.facets:
            output["facets"] = [
                SearchResponse.Facet.to_dict(facet) for facet in pager.facets
            ]

        if pager.guided_search_result:
            output["guided_search_result"] = SearchResponse.GuidedSearchResult.to_dict(
                pager.guided_search_result
            )

        if pager.query_expansion_info:
            output["query_expansion_info"] = SearchResponse.QueryExpansionInfo.to_dict(
                pager.query_expansion_info
            )

        if pager.applied_controls:
            output["applied_controls"] = [
                control.strip() for control in pager.applied_controls
            ]

        return output

    def simplify_search_results(self, response: dict[str, Any]) -> dict[str, Any]:
        """
        Simplify the search results by parsing documents and chunks.

        Args:
            response (Dict[str, Any]): The raw search response.

        Returns:
            Dict[str, Any]: The simplified search results.
        """
        if "results" not in response:
            return response
        simplified_results = []
        for result in response["results"]:
            if "document" in result:
                simplified_results.append(
                    self._parse_document_result(result["document"])
                )
            elif "chunk" in result:
                simplified_results.append(self._parse_chunk_result(result["chunk"]))
        response["simplified_results"] = simplified_results
        return response

    def _parse_document_result(self, document: dict[str, Any]) -> dict[str, Any]:
        """
        Parse a single document result from the search response.

        This supports both structured and unstructured data, and also supports
        extractive segments and answers and snippets.

        Args:
            document (Dict[str, Any]): The document data from the search result.

        Returns:
            Dict[str, Any]: The parsed document page_content and metadata.
        """
        metadata = {
            **document.get("derived_struct_data", {}),
            **document.get("struct_data", {}),
        }

        json_data = document.get("json_data", {})
        if isinstance(json_data, str):
            try:
                json_data = json.loads(json_data)
            except json.JSONDecodeError:
                print(f"Warning: Failed to parse json_data: {json_data}")
                json_data = {}

        metadata.update(json_data)
        result: dict[str, Any] = {"metadata": metadata}

        if self.config.engine_data_type == "STRUCTURED":
            structured_data = (
                json_data if json_data else document.get("struct_data", {})
            )
            result["page_content"] = json.dumps(structured_data, indent=2)
            for key in structured_data.keys():
                result["metadata"].pop(key, None)
        elif "extractive_answers" in metadata:
            result["page_content"] = self._parse_segments(
                metadata.get("extractive_answers", [])
            )
        elif "snippets" in metadata:
            result["page_content"] = self._parse_snippets(metadata.get("snippets", []))
        else:
            result["page_content"] = metadata.get("content", "")

        return result

    def _parse_segments(self, segments: list[dict[str, Any]]) -> str:
        """
        Parse extractive segments from a single document of search results.

        Args:
            segments (List[Dict[str, Any]]): The list of extractive segments.

        Returns:
            str: A formatted string containing page number, score and the text of each segment.
        """
        parsed_segments = [
            {
                "content": self._strip_content(segment.get("content", "")),
                "page_number": segment.get("page_number") or segment.get("pageNumber"),
                "score": segment.get("score"),
            }
            for segment in segments
        ]
        return "\n\n".join(
            f"On page {segment['page_number']} with a relevance score of {segment['score']}:\n"
            f"```\n{segment['content']}\n```"
            for segment in parsed_segments
        )

    def _parse_snippets(self, snippets: list[dict[str, Any]]) -> str:
        """
        Parse snippets from a single document of search results.

        Args:
            snippets (List[Dict[str, Any]]): The list of snippets.

        Returns:
            str: A formatted string containing the successfully parsed snippets.
        """
        return "\n\n".join(
            self._strip_content(snippet.get("snippet", ""))
            for snippet in snippets
            if snippet.get("snippetStatus") == "SUCCESS"
        )

    def _parse_chunk_result(self, chunk: dict[str, Any]) -> dict[str, Any]:
        """
        Parse a single chunk result from the search response.

        Args:
            chunk (Dict[str, Any]): The chunk data from the search result.

        Returns:
            Dict[str, Any]: The parsed chunk page_content and metadata.
        """
        metadata = {
            "chunk_id": chunk.get("id"),
            "score": chunk.get("relevance_score"),
        }

        page_span = chunk.get("page_span", {})
        if page_span:
            metadata["page"] = page_span.get("page_start")
            metadata["page_span_end"] = page_span.get("page_end")

        metadata.update(chunk.get("document_metadata", {}))
        metadata.update(chunk.get("derived_struct_data", {}))

        return {
            "metadata": metadata,
            "page_content": self._strip_content(chunk.get("content", "")),
        }

    @staticmethod
    def _strip_content(text: str) -> str:
        """
        Strip HTML tags and unescape HTML entities from the given text.

        Args:
            text (str): The input text to clean.

        Returns:
            str: The cleaned text.
        """
        text = re.sub("<.*?>", "", text)
        return html.unescape(text).strip()
