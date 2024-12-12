from typing import List
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud.discoveryengine_v1.types import SearchResponse
from src.model.search import SearchApplication
import google.auth

_, PROJECT_ID = google.auth.default()


class SearchService():

    def __init__(self, application: SearchApplication):
        client_options = (
            ClientOptions(api_endpoint=f"{application.region}-discoveryengine.googleapis.com")
            if application.region != "global"
            else None
        )
        self.client = discoveryengine.SearchServiceClient(client_options=client_options)
        self.serving_config = f"projects/{PROJECT_ID}/locations/{application.region}/collections/default_collection/engines/{application.engine_id}/servingConfigs/default_config"
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
        for r in response.results:
            # TODO: Do a proper mapping of results to Python classes
            print(r.document)

        return results