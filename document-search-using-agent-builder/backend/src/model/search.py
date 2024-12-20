from dataclasses import dataclass, field
from typing import List, Optional
from pydantic import BaseModel
from google.cloud.bigquery import SchemaField
from google.api_core.client_options import ClientOptions
import google.auth

_, PROJECT_ID = google.auth.default()

class CreateSearchRequest(BaseModel):
    term: str

class SearchApplication(BaseModel):
    engine_id: str
    region: str

    def __schema__() -> List[SchemaField]:
        return [
            SchemaField("engine_id", "STRING", mode="REQUIRED"),
            SchemaField("region", "STRING", mode="REQUIRED")
        ]
    
    def __from_row__(row):
        return SearchApplication(
            engine_id=row[0],
            region=row[1]
        )

    def to_dict(self):
        return {
            "engine_id": self.engine_id,
            "region": self.region,
        }
    
    def to_insert_string(self):
        return f'"{self.engine_id}", "{self.region}"'
    
    def get_client_options(self) -> Optional[ClientOptions]:
        return ClientOptions(api_endpoint=f"{self.region}-discoveryengine.googleapis.com") if self.region != "global" else None
    
    def get_serving_config(self) -> str:
        return f"projects/{PROJECT_ID}/locations/{self.region}/collections/default_collection/engines/{self.engine_id}/servingConfigs/default_config"

class Engine(BaseModel):
    name: str
    engine_id: str
    region: str

@dataclass
class SearchResult:
    document_id: str
    title: str
    snippet: str
    link: Optional[str] = None
    content: Optional[str] = None

@dataclass
class SearchResultsWithSummary:
    results: List[SearchResult]
    summary: Optional[str] = None        