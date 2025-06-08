import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from google.cloud import firestore

from agents.orchestrator import Orchestrator
from config.logging_config import setup_logging
from config.settings import API_CONFIG
from models.gemini_client import GeminiClient
from tools.analysis_tools import AnalysisTools
from tools.dataset_tools import DatasetTools
from tools.document_tools import DocumentTools
from tools.search_tools import SearchTools
from workflows.research_workflow import create_research_workflow
from workflows.resource_workflow import create_resource_workflow
from workflows.use_case_workflow import create_use_case_workflow

# Setup logging
logger = setup_logging()

# Firestore persistent storage implementation
class FirestoreAnalysisStore:
    def __init__(self):
        self.db = firestore.Client()
        self.collection = self.db.collection('analyses')
    
    async def create_analysis(self, request_id: str, analysis_data: Dict[str, Any]) -> None:
        """Create a new analysis record."""
        doc_data = {
            **analysis_data,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        await asyncio.get_event_loop().run_in_executor(
            None, 
            self.collection.document(request_id).set, 
            doc_data
        )
    
    async def update_analysis(self, request_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing analysis record."""
        updates['updated_at'] = datetime.utcnow()
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.collection.document(request_id).update,
            updates
        )
    
    async def get_analysis(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get an analysis by request ID."""
        doc = await asyncio.get_event_loop().run_in_executor(
            None,
            self.collection.document(request_id).get
        )
        return doc.to_dict() if doc.exists else None
    
    async def set_status(self, request_id: str, status: str, error: Optional[str] = None) -> None:
        """Update analysis status."""
        updates = {'status': status, 'updated_at': datetime.utcnow()}
        if error:
            updates['error'] = error
        await self.update_analysis(request_id, updates)

# Initialize FastAPI app
app = FastAPI(
    title="AI Market Analyst API",
    description="API for generating AI and Gen AI use cases for companies and industries",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://*.web.app",      # Firebase Hosting
        "https://*.firebaseapp.com",  # Firebase Hosting
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Initialize components
llm = GeminiClient()
search_tools = SearchTools()
dataset_tools = DatasetTools()
analysis_tools = AnalysisTools(llm)
document_tools = DocumentTools()

# Initialize workflows
research_workflow = create_research_workflow(llm, search_tools)
use_case_workflow = create_use_case_workflow(llm, analysis_tools)
resource_workflow = create_resource_workflow(llm, dataset_tools)

# Initialize orchestrator and Firestore store
orchestrator = Orchestrator(llm)
analysis_store = FirestoreAnalysisStore()


# Define request and response models
class AnalysisRequest(BaseModel):
    company_name: Optional[str] = Field(None, description="Name of the company")
    industry_name: Optional[str] = Field(None, description="Name of the industry")
    num_use_cases: int = Field(5, description="Number of use cases to generate")


class UseCaseResponse(BaseModel):
    title: str
    description: str
    business_value: str
    implementation_complexity: str
    ai_technologies: List[str]
    priority_score: Optional[float] = None
    keywords: Optional[List[str]] = None
    cross_functional_benefits: Optional[List[Dict[str, str]]] = None


class ResourceResponse(BaseModel):
    title: str
    url: str
    description: str
    source: str
    relevance_score: Optional[float] = None
    relevance_notes: Optional[str] = None


class AnalysisResponse(BaseModel):
    request_id: str
    status: str
    company_info: Optional[Dict[str, Any]] = None
    industry_info: Optional[Dict[str, Any]] = None
    use_cases: Optional[List[UseCaseResponse]] = None
    resources: Optional[Dict[str, List[ResourceResponse]]] = None
    markdown: Optional[str] = None


async def run_analysis(
    request_id: str,
    company_name: Optional[str],
    industry_name: Optional[str],
    num_use_cases: int,
):
    """Run the analysis workflow in the background."""
    try:
        # Update status to running
        await analysis_store.set_status(request_id, "running")

        # Run orchestrator
        result = await orchestrator.generate_use_cases(
            company_name=company_name,
            industry_name=industry_name,
            num_use_cases=num_use_cases,
        )

        # Update analysis with results
        await analysis_store.update_analysis(request_id, {
            "status": "completed",
            "company_info": result.get("company_info", {}),
            "industry_info": result.get("industry_info", {}),
            "use_cases": result.get("use_cases", []),
            "resources": result.get("resources", {}),
            "markdown": result.get("markdown", ""),
            "markdown_path": result.get("markdown_path", ""),
            "json_path": result.get("json_path", ""),
            "completed_at": datetime.utcnow().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error running analysis: {e}")
        await analysis_store.set_status(request_id, "failed", str(e))


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Start an analysis process."""
    if not request.company_name and not request.industry_name:
        raise HTTPException(
            status_code=400,
            detail="Either company_name or industry_name must be provided",
        )

    # Generate a request ID
    request_id = str(uuid.uuid4())

    # Initialize analysis in Firestore
    await analysis_store.create_analysis(request_id, {
        "request_id": request_id,
        "status": "pending",
        "company_name": request.company_name,
        "industry_name": request.industry_name,
        "num_use_cases": request.num_use_cases,
    })

    # Start analysis in background
    background_tasks.add_task(
        run_analysis,
        request_id=request_id,
        company_name=request.company_name,
        industry_name=request.industry_name,
        num_use_cases=request.num_use_cases,
    )

    return AnalysisResponse(request_id=request_id, status="pending")


@app.get("/api/analysis/{request_id}", response_model=AnalysisResponse)
async def get_analysis(request_id: str):
    """Get the status and results of an analysis."""
    analysis = await analysis_store.get_analysis(request_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return AnalysisResponse(
        request_id=analysis["request_id"],
        status=analysis["status"],
        company_info=analysis.get("company_info"),
        industry_info=analysis.get("industry_info"),
        use_cases=analysis.get("use_cases"),
        resources=analysis.get("resources"),
        markdown=analysis.get("markdown"),
    )


@app.get("/api/markdown/{request_id}")
async def get_markdown(request_id: str):
    """Get the markdown output for an analysis."""
    analysis = await analysis_store.get_analysis(request_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis["status"] != "completed":
        raise HTTPException(status_code=400, detail="Analysis not yet completed")

    if "markdown" not in analysis:
        raise HTTPException(status_code=400, detail="Markdown not available")

    return JSONResponse(content={"markdown": analysis["markdown"]})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=API_CONFIG["host"],
        port=API_CONFIG["port"],
        reload=API_CONFIG["debug"],
    )