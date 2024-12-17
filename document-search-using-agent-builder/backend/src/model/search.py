from dataclasses import dataclass, field
from typing import List, Optional
from pydantic import BaseModel
from google.cloud.bigquery import SchemaField
from google.api_core.client_options import ClientOptions
import google.auth

_, PROJECT_ID = google.auth.default()

@dataclass
class Snippet:
    snippet_status: str
    snippet: str

@dataclass
class ExtractiveAnswer:
    pageNumber: str
    content: str

@dataclass
class DerivedStructData:
    link: Optional[str]
    source_type: Optional[str]
    title: Optional[str]
    entity_type: Optional[str]
    extractive_answers: List[ExtractiveAnswer] = field(default_factory=list)
    snippets: List[Snippet] = field(default_factory=list)

@dataclass
class Document:
    name: str
    id: str
    derivedStructData: DerivedStructData

@dataclass
class Result:
    id: str
    document: Document

@dataclass
class ResponseModel:
    term: Optional[str]
    results: List[Result]
    totalSize: int
    attributionToken: str
    guidedSearchResult: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    queryExpansionInfo: dict = field(default_factory=dict)

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