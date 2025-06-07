import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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

# Initialize FastAPI app
app = FastAPI(
    title="AI Market Analyst API",
    description="API for generating AI and GenAI use cases for companies and industries",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
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

# Initialize orchestrator
orchestrator = Orchestrator(llm)


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


# Store ongoing analyses
analyses = {}


async def run_analysis(
    request_id: str,
    company_name: Optional[str],
    industry_name: Optional[str],
    num_use_cases: int,
):
    """Run the analysis workflow in the background."""
    try:
        # Update status to running
        analyses[request_id]["status"] = "running"

        # Run orchestrator
        result = await orchestrator.generate_use_cases(
            company_name=company_name,
            industry_name=industry_name,
            num_use_cases=num_use_cases,
        )

        # Update analysis with results
        analyses[request_id].update(
            {
                "status": "completed",
                "company_info": result.get("company_info", {}),
                "industry_info": result.get("industry_info", {}),
                "use_cases": result.get("use_cases", []),
                "resources": result.get("resources", {}),
                "markdown": result.get("markdown", ""),
                "markdown_path": result.get("markdown_path", ""),
                "json_path": result.get("json_path", ""),
                "completed_at": result.get("completed_at", ""),
            }
        )

    except Exception as e:
        logger.error(f"Error running analysis: {e}")
        analyses[request_id]["status"] = "failed"
        analyses[request_id]["error"] = str(e)


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

    # Initialize analysis
    analyses[request_id] = {
        "request_id": request_id,
        "status": "pending",
        "company_name": request.company_name,
        "industry_name": request.industry_name,
        "num_use_cases": request.num_use_cases,
        "created_at": None,
    }

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
    if request_id not in analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis = analyses[request_id]

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
    if request_id not in analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis = analyses[request_id]

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
