import requests
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class SearchResult:
    document_id: str
    title: str
    snippet: str
    link: Optional[str] = None
    formatted_url: Optional[str] = None

class SearchService:

    def __init__(self, api_url: str):
        self.api_url = api_url  # Base URL to query directly

    def search(self, term: str) -> List[SearchResult]:
        payload = {
            "query": term,
            "page_size": 10,
            "query_expansion_spec": {
                "condition": "AUTO"
            },
            "spell_correction_spec": {
                "mode": "AUTO"
            },
            "content_search_spec": {
                "extractive_content_spec": {
                    "max_extractive_answer_count": 1
                },
                "snippet_spec": {
                    "return_snippet": True
                }
            }
        }

        # Perform the HTTP POST request
        response = requests.post(self.api_url, json=payload)
        response.raise_for_status()  # Raise an error if the request fails

        data = response.json()  # Parse JSON response
        results = []

        # Process results
        for r in data.get("results", []):
            document = r.get("document", {})
            derived_data = document.get("derivedStructData", {})

            # Extract snippet safely
            snippets = derived_data.get("snippets", [])
            snippet_text = snippets[0].get("snippet", "No snippet available") if snippets else "No snippet available"

            # Map to SearchResult
            mapped_result = SearchResult(
                document_id=document.get("id", "Unknown"),
                title=derived_data.get("title", "Untitled"),
                snippet=snippet_text,
                link=derived_data.get("link"),
                formatted_url=derived_data.get("formattedUrl"),
            )
            results.append(mapped_result)

        return results


def get_token():
    """
    Fetches an authentication token from the metadata server.
    """
    
    metadata_server_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
    headers = {
        'Metadata-Flavor': 'Google'
    }

    try:
        response = requests.get(metadata_server_url, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        token_data = response.json()  # Parse the JSON response
        access_token = token_data['access_token'].strip()  # Extract the access_token
        return access_token

    except requests.exceptions.RequestException as e:
        print(f"Error fetching token: {e}")
        raise