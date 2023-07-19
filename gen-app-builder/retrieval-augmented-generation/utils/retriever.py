"""Retriever wrapper for Google Cloud Enterprise Search."""
# pylint: disable=no-self-argument
from __future__ import annotations

from typing import Any, Dict, List, Optional

from google.cloud import discoveryengine_v1beta
from google.cloud.discoveryengine_v1beta.services.search_service import pagers
from langchain.schema import BaseRetriever, Document
from langchain.utils import get_from_dict_or_env
from pydantic import BaseModel, Extra, Field, root_validator


class EnterpriseSearchRetriever(BaseRetriever, BaseModel):
    """Wrapper around Google Cloud Enterprise Search Service API."""

    _client: Any
    _serving_config: Any
    project_id: str
    search_engine_id: str
    serving_config_id: str = "default_config"
    location_id: str = "global"
    filter: Optional[str] = None
    get_extractive_answers: bool = False
    max_documents: int = Field(default=5, ge=1, le=100)
    max_extractive_answer_count: int = Field(default=1, ge=1, le=5)
    max_extractive_segment_count: int = Field(default=1, ge=1, le=1)
    query_expansion_condition: int = Field(default=1, ge=0, le=2)
    credentials: Any = None
    "The default custom credentials (google.auth.credentials.Credentials) to use "
    "when making API calls. If not provided, credentials will be ascertained from "
    "the environment."

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        try:
            from google.cloud import discoveryengine_v1beta  # noqa: F401
        except ImportError:
            raise ImportError(
                "google.cloud.discoveryengine is not installed. "
                "Please install it with pip install google-cloud-discoveryengine"
            )

        values["project_id"] = get_from_dict_or_env(values, "project_id", "PROJECT_ID")
        values["search_engine_id"] = get_from_dict_or_env(
            values, "search_engine_id", "SEARCH_ENGINE_ID"
        )

        return values

    def __init__(self, **data):
        super().__init__(**data)
        self._client = discoveryengine_v1beta.SearchServiceClient(
            credentials=self.credentials
        )
        self._serving_config = self._client.serving_config_path(
            project=self.project_id,
            location=self.location_id,
            data_store=self.search_engine_id,
            serving_config=self.serving_config_id,
        )

    def _convert_search_response(
        self, search_results: pagers.SearchPager
    ) -> List[Document]:
        """Converts search response to a list of LangChain documents."""
        documents = []
        for result in search_results:
            if hasattr(result.document, "derived_struct_data"):
                metadata = getattr(result.document, "struct_value", {})
                doc_data = result.document.derived_struct_data
                chunk_type = (
                    "extractive_answers"
                    if self.get_extractive_answers
                    else "extractive_segments"
                )
                for chunk in doc_data.get(chunk_type, []):
                    if chunk_type == "extractive_answers":
                        metadata[
                            "source"
                        ] = f"{doc_data.get('link', '')}:{chunk.get('pageNumber', '')}"
                    else:
                        metadata["source"] = f"{doc_data.get('link', '')}"
                    metadata["id"] = result.document.id
                    documents.append(
                        Document(
                            page_content=chunk.get("content", ""), metadata=metadata
                        )
                    )

        return documents

    def _create_search_request(
        self, query: str
    ) -> discoveryengine_v1beta.SearchRequest:
        """Prepares a SearchRequest object."""

        if self.get_extractive_answers:
            content_search_spec = {
                "extractive_content_spec": {
                    "max_extractive_answer_count": self.max_extractive_answer_count,
                }
            }
        else:
            content_search_spec = {
                "extractive_content_spec": {
                    "max_extractive_segment_count": self.max_extractive_segment_count,
                }
            }

        query_expansion_spec = {
            "condition": self.query_expansion_condition,
        }

        request = discoveryengine_v1beta.SearchRequest(
            query=query,
            filter=self.filter,
            serving_config=self._serving_config,
            page_size=self.max_documents,
            content_search_spec=content_search_spec,
            query_expansion_spec=query_expansion_spec,
        )

        return request

    def get_relevant_documents(self, query: str) -> List[Document]:
        """Get documents relevant for a query."""

        request = self._create_search_request(query)
        response = self._client.search(request)
        documents = self._convert_search_response(response.results)

        return documents

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        raise NotImplementedError("Async interface to GDELT not implemented")
