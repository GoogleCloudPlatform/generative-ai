from dataclasses import dataclass, field
from typing import List, Optional
from pydantic import BaseModel, HttpUrl

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
    region: str
    engine_id: str