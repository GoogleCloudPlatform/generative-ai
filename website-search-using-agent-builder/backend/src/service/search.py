from typing import List, Optional
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud.discoveryengine_v1.types import SearchResponse
from src.model.search import SearchApplication
import google.auth
from dataclasses import dataclass

_, PROJECT_ID = google.auth.default()

@dataclass
class SearchResult:
    document_id: str
    title: str
    snippet: str
    link: Optional[str] = None
    formatted_url: Optional[str] = None

class SearchService():

    def __init__(self, application: SearchApplication):
        client_options = (
            ClientOptions(api_endpoint=f"{application.region}-discoveryengine.googleapis.com")
            if application.region != "global"
            else None
        )
        self.client = discoveryengine.SearchServiceClient(client_options=client_options)
        self.serving_config = f"projects/{PROJECT_ID}/locations/{application.region}/collections/default_collection/engines/{application.engine_id}/servingConfigs/default_search"
        # f"https://discoveryengine.googleapis.com/v1alpha/projects/{item.project_id}/locations/{item.location}/"
        # f"dataStores/{item.engine_id}/servingConfigs/{item.serving_config}:search"
        # "projects/318457139342/locations/global/collections/default_collection/engines/robin-search-app-2_1733237288232/servingConfigs/default_search",
        self.content_search_config = discoveryengine.SearchRequest.ContentSearchSpec(
            extractive_content_spec= discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                max_extractive_answer_count=1
            ),
            snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                return_snippet=True
            ),
        )

    def search(self, term: str) -> List[discoveryengine.SearchResponse]:
        request = discoveryengine.SearchRequest(
            serving_config=self.serving_config,
            query=term,
            page_size=10,
            content_search_spec=self.content_search_config,
            query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
                condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
            ),
            spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            ),
        )

        response: SearchResponse = self.client.search(request)
        results = []
        # print(response.results)
        for r in response.results:
            document = r.document
            derived_data = document.derived_struct_data or {}

            print("derived data - ", derived_data)

            # Extract snippet safely (it's a list of dicts in the example)
            snippets = derived_data.get("snippets", [])
            snippet_text = snippets[0].get("snippet", "No snippet available") if snippets else "No snippet available"

            # Map to SearchResult
            mapped_result = SearchResult(
                document_id=document.id,
                title=derived_data.get("title", "Untitled"),
                snippet=snippet_text,
                link=derived_data.get("link"),
                formatted_url=derived_data.get("formattedUrl"),
            )
            results.append(mapped_result)

        return results