"""Retriever wrapper for Google Cloud Enterprise Search."""
# pylint: disable=no-self-argument
from __future__ import annotations

from typing import Any, Dict, List

from google.cloud import discoveryengine_v1beta
from google.cloud.discoveryengine_v1beta.services.search_service import pagers
from langchain.schema import BaseRetriever, Document
from langchain.utils import get_from_dict_or_env
from pydantic import BaseModel, Extra, root_validator


class EnterpriseSearchRetriever(BaseRetriever, BaseModel):
    """Wrapper around Google Cloud Enterprise Search."""

    client: Any = None  #: :meta private:
    serving_config: Any = None  #: :meta private:Any
    content_search_spec: Any = None  #: :meta private:Any
    project_id: str = ""
    search_engine_id: str = ""
    serving_config_id: str = "default_config"
    location_id: str = "global"
    max_snippet_count: int = 3
    credentials: Any = None
    "The default custom credentials (google.auth.credentials.Credentials) to use "
    "when making API calls. If not provided, credentials will be ascertained from "
    "the environment."

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid
        arbitrary_types_allowed = True

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        try:
            from google.cloud import discoveryengine_v1beta
        except ImportError:
            raise ImportError(
                "google.cloud.discoveryengine is not installed. "
                "Please install it with pip install google-cloud-discoveryengine"
            )

        project_id = get_from_dict_or_env(values, "project_id", "PROJECT_ID")
        values["project_id"] = project_id
        search_engine_id = get_from_dict_or_env(
            values, "search_engine_id", "SEARCH_ENGINE_ID"
        )
        values["search_engine_id"] = search_engine_id
        location_id = get_from_dict_or_env(values, "location_id", "LOCATION_ID")
        values["location_id"] = location_id
        max_snippet_count = get_from_dict_or_env(
            values, "max_snippet_count", "MAX_SNIPPET_COUNT"
        )
        values["max_snippet_count"] = max_snippet_count

        client = discoveryengine_v1beta.SearchServiceClient(
            credentials=values["credentials"]
        )
        values["client"] = client

        serving_config = client.serving_config_path(
            project=project_id,
            location=location_id,
            data_store=search_engine_id,
            serving_config=values["serving_config_id"],
        )
        values["serving_config"] = serving_config

        content_search_spec = {
            "snippet_spec": {
                "max_snippet_count": max_snippet_count,
            }
        }
        values["content_search_spec"] = content_search_spec

        return values

    def _convert_search_response(
        self, search_results: pagers.SearchPager
    ) -> List[Document]:
        """Converts search response to a list of LangChain documents."""
        documents = []
        for result in search_results:
            if hasattr(result.document, "derived_struct_data"):
                doc_data = result.document.derived_struct_data
                for snippet in doc_data.get("snippets", []):
                    documents.append(
                        Document(
                            page_content=snippet.get("snippet", ""),
                            metadata={
                                "source": f"{doc_data.get('link', '')}:{snippet.get('pageNumber', '')}",
                                "id": result.document.id,
                            },
                        )
                    )
        return documents

    def get_relevant_documents(self, query: str) -> List[Document]:
        """Get documents relevant for a query."""
        request = discoveryengine_v1beta.SearchRequest(
            query=query,
            serving_config=self.serving_config,
            content_search_spec=self.content_search_spec,
        )
        response = self.client.search(request)
        documents = self._convert_search_response(response.results)

        return documents

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        raise NotImplementedError("Async interface to GDELT not implemented")
