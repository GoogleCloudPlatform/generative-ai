from fastapi import APIRouter, Request, HTTPException, Response
from src.model.search import CreateSearchRequest, SearchApplication
from src.model.http_status import BadRequest
from src.model.search import CreateSearchRequest, SearchApplication

from src.service.engine import EngineService
from src.service.search import SearchService
from src.service.search_application import SearchApplicationService
from google.cloud import storage
import datetime
from pydantic import BaseModel


class SignedUrlRequest(BaseModel):
    gcs_url: str

storage_client = storage.Client()    

router = APIRouter(
    prefix="/api/search",
    tags=["searches"],
    responses={404: {"description": "Not found"}},
)

@router.post("")
async def search(item: CreateSearchRequest):
    service = SearchApplicationService()
    search_application = service.get()
    if not search_application: raise BadRequest(detail=f"No Search Application found on project") 

    service = SearchService(
        search_application,
    )
    return service.search(item.term)

@router.get("/engines")
async def get_all_engines():
    service = EngineService()
    return service.get_all()

@router.get("/application")
async def get_search_application():
    service = SearchApplicationService()
    return service.get()

@router.post("/application")
async def create_search_application(search_application: SearchApplication):
    service = SearchApplicationService()
    return service.create(search_application)

@router.put("/application/{engine_id}")
async def update_search_application(engine_id: str, search_application: SearchApplication):
    service = SearchApplicationService()
    return service.update(engine_id, search_application)


@router.post("/doc")
async def get_document(request: Request, response_model=None):
    """
    Generates a signed URL for a file in Google Cloud Storage.

    Args:
        gcs_url: The full GCS URL of the file 
                 (e.g., "gs://your-bucket-name/your-file.pdf").
        expiration_hours: The number of hours the signed URL should be valid for.
                          Defaults to 1 hour.
    """
    try:
        req_body = await request.json()
        signed_url_request = SignedUrlRequest(**req_body)
        gcs_url = signed_url_request.gcs_url

        bucket_name = gcs_url.split("/")[2]
        object_name = "/".join(gcs_url.split("/")[3:])

        # Get a reference to the blob (PDF file)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)

        # Download the blob content as bytes
        pdf_content = blob.download_as_bytes()

        # Return the PDF content with appropriate headers
        return Response(content=pdf_content, media_type="application/pdf")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching PDF: {str(e)}")