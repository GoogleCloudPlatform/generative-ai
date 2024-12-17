import requests
from typing import List, Optional
from dataclasses import dataclass
from typing import List
from google.cloud.discoveryengine_v1 import SearchRequest, SearchServiceClient
from src.model.search import SearchApplication, SearchResult

CONTENT_SEARCH_SPEC = SearchRequest.ContentSearchSpec(
    snippet_spec=SearchRequest.ContentSearchSpec.SnippetSpec(
        return_snippet=True
    ),
    extractive_content_spec=SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
        max_extractive_answer_count=1
    )
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

        # payload = {
        #     "query": term,
        #     "page_size": 10,
        #     "query_expansion_spec": {
        #         "condition": "AUTO"
        #     },
        #     "spell_correction_spec": {
        #         "mode": "AUTO"
        #     },
        #     "content_search_spec": {
        #         "extractive_content_spec": {
        #             "max_extractive_answer_count": 1
        #         },
        #         "snippet_spec": {
        #             "return_snippet": True
        #         }
        #     }
        # }

        # token = get_token()
        # headers = {
        #     'Authorization': f'Bearer {token}',
        #     "Content-Type": "application/json"
        # }

        # # Perform the HTTP POST request
        # response = requests.post(self.api_url, headers=headers, json=payload)
        # response.raise_for_status()  # Raise an error if the request fails

        # data = response.json()
        # results = []

        # Process results
        for r in data.results:
            document = r.document
            derived_data = document.derived_struct_data

            # Extract snippet safely
            snippets = derived_data.get("snippets", [])
            snippet_text = snippets[0].get("snippet", "No snippet available") if snippets else "No snippet available"
            extractive_answers = derived_data.get("extractive_answers", [])
            content_text = extractive_answers[0].get("content", "No content available") if extractive_answers else "No content available"
            # Map to SearchResult
            mapped_result = SearchResult(
                document_id=document.id,
                title=derived_data.get("title", "Untitled"),
                snippet=snippet_text,
                link=derived_data.get("link"),
                content=content_text
            )
            results.append(mapped_result)

        return results


# def get_token():
#     """
#     Fetches an authentication token from the metadata server.
#     """
    
#     metadata_server_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
#     headers = {
#         'Metadata-Flavor': 'Google'
#     }

#     try:
#         response = requests.get(metadata_server_url, headers=headers)
#         response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
#         token_data = response.json()  # Parse the JSON response
#         access_token = token_data['access_token'].strip()  # Extract the access_token
#         return access_token

#     except requests.exceptions.RequestException as e:
#         print(f"Error fetching token: {e}")
#         raise