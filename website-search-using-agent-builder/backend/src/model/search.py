from fastapi import APIRouter
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict

class CseImage(BaseModel):
    src: HttpUrl

class CseThumbnail(BaseModel):
    src: HttpUrl
    height: str
    width: str

class DocumentMetaTag(BaseModel):
    google_signin_client_id: Optional[str]
    google_signin_scope: Optional[str]
    og_description: Optional[str]
    og_image: Optional[HttpUrl]
    og_image_height: Optional[str]
    og_image_width: Optional[str]
    og_locale: Optional[str]
    og_site_name: Optional[str]
    og_title: Optional[str]
    og_type: Optional[str]
    og_url: Optional[HttpUrl]
    theme_color: Optional[str]
    twitter_card: Optional[str]
    viewport: Optional[str]

class Snippet(BaseModel):
    htmlSnippet: Optional[str]
    snippet: Optional[str]

class DerivedStructData(BaseModel):
    displayLink: Optional[str]
    formattedUrl: Optional[HttpUrl]
    htmlFormattedUrl: Optional[HttpUrl]
    htmlTitle: Optional[str]
    link: Optional[HttpUrl]
    pagemap: Optional[Dict[str, List]]
    snippets: Optional[List[Snippet]]
    title: Optional[str]

class Document(BaseModel):
    derivedStructData: Optional[DerivedStructData]
    id: Optional[str]
    name: Optional[str]

class Result(BaseModel):
    document: Document
    id: Optional[str]

class ResponseModel(BaseModel):
    search: Optional[str]
    attributionToken: Optional[str]
    guidedSearchResult: Optional[Dict]
    results: List[Result]
    summary: Optional[Dict]
    totalSize: Optional[int]

class CreateSearchRequest(BaseModel):
    search: str