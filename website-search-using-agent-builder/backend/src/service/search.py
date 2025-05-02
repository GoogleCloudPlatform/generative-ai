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

    def __init__(self, search_application: SearchApplication):
        self.search_client = SearchServiceClient(
            client_options=search_application.get_client_options()
        )
        self.serving_config = search_application.get_serving_config()

    def search(self, term: str) -> List[SearchResult]:
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
