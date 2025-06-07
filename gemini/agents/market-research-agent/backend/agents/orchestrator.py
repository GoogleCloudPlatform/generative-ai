import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from langfuse.client import Langfuse

from config.settings import (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY,
                             MONITORING_CONFIG)
from models.gemini_client import GeminiClient
from models.llm_interface import LLMInterface
from tools.analysis_tools import AnalysisTools
from tools.dataset_tools import DatasetTools
from tools.document_tools import DocumentTools
from tools.search_tools import SearchTools

from .industry_research_agent import IndustryResearchAgent
from .resource_collection_agent import ResourceCollectionAgent
from .use_case_generation_agent import UseCaseGenerationAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    """Orchestrator for coordinating agent workflows."""

    def __init__(self, llm: Optional[LLMInterface] = None):
        """Initialize the orchestrator.

        Args:
            llm: Optional LLM interface. If not provided, a GeminiClient will be created.
        """
        # Initialize LLM if not provided
        self.llm = llm if llm is not None else GeminiClient()

        # Initialize tools
        self.search_tools = SearchTools()
        self.dataset_tools = DatasetTools()
        self.analysis_tools = AnalysisTools(self.llm)
        self.document_tools = DocumentTools()

        # Initialize agents
        self.industry_research_agent = IndustryResearchAgent(
            self.llm, self.search_tools
        )
        self.use_case_generation_agent = UseCaseGenerationAgent(
            self.llm, self.analysis_tools
        )
        self.resource_collection_agent = ResourceCollectionAgent(
            self.llm, self.dataset_tools
        )

        # Initialize monitoring
        self.monitoring_enabled = MONITORING_CONFIG["enabled"]
        if self.monitoring_enabled and LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
            try:
                self.langfuse = Langfuse(
                    public_key=LANGFUSE_PUBLIC_KEY,
                    secret_key=LANGFUSE_SECRET_KEY,
                    host=MONITORING_CONFIG.get("langfuse_host"),
                )
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse: {e}")
                self.monitoring_enabled = False
        else:
            self.monitoring_enabled = False

    async def generate_use_cases(
        self,
        company_name: Optional[str] = None,
        industry_name: Optional[str] = None,
        num_use_cases: int = 5,
    ) -> Dict[str, Any]:
        """Generate AI/GenAI use cases for a company/industry.

        Args:
            company_name: Optional name of the company.
            industry_name: Optional name of the industry.
            num_use_cases: Number of use cases to generate.

        Returns:
            Dictionary containing generated use cases and other information.
        """
        if not company_name and not industry_name:
            raise ValueError("Either company_name or industry_name must be provided")

        # Generate trace ID for monitoring
        trace_id = str(uuid.uuid4())

        # Start monitoring trace if enabled
        trace = None
        if self.monitoring_enabled:
            try:
                trace = self.langfuse.trace(
                    name="use_case_generation",
                    id=trace_id,
                    metadata={
                        "company_name": company_name,
                        "industry_name": industry_name,
                        "num_use_cases": num_use_cases,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to create Langfuse trace: {e}")

        try:
            # Step 1: Research industry and company
            span = None
            if self.monitoring_enabled and trace:
                try:
                    span = trace.span(name="industry_research")
                except Exception as e:
                    logger.error(f"Failed to create Langfuse span: {e}")

            company_info, industry_info = await self.industry_research_agent.research(
                company_name=company_name, industry_name=industry_name
            )

            if self.monitoring_enabled and span:
                try:
                    if hasattr(span, "end"):
                        span.end()
                except Exception as e:
                    logger.error(f"Failed to end Langfuse span: {e}")

            # Step 2: Generate use cases
            logger.info("Step 2: Generating use cases")
            if self.monitoring_enabled:
                span = trace.span(name="use_case_generation")
                span.start()

            use_cases = await self.use_case_generation_agent.generate_use_cases(
                company_info=company_info,
                industry_info=industry_info,
                num_use_cases=num_use_cases,
            )

            if self.monitoring_enabled and trace:
                try:
                    if hasattr(trace, "end"):
                        trace.end()
                except Exception as e:
                    logger.error(f"Failed to end Langfuse trace: {e}")

            # Step 3: Collect resources
            logger.info("Step 3: Collecting resources")
            if self.monitoring_enabled:
                span = trace.span(name="resource_collection")
                span.start()

            resources = await self.resource_collection_agent.collect_resources(
                use_cases=use_cases
            )

            if self.monitoring_enabled and trace:
                try:
                    if hasattr(trace, "end"):
                        trace.end()
                except Exception as e:
                    logger.error(f"Failed to end Langfuse trace: {e}")

            # Step 4: Format results
            logger.info("Step 4: Formatting results")
            if self.monitoring_enabled:
                span = trace.span(name="document_generation")
                span.start()

            markdown = self.document_tools.format_use_cases_markdown(
                use_cases=use_cases,
                company_info=company_info,
                industry_info=industry_info,
                resources=resources,
            )

            markdown_path = self.document_tools.save_use_cases_markdown(
                markdown=markdown, company_name=company_name or industry_name
            )

            json_path = self.document_tools.save_use_cases_json(
                use_cases=use_cases,
                company_info=company_info,
                industry_info=industry_info,
                resources=resources,
                company_name=company_name or industry_name,
            )

            if self.monitoring_enabled:
                span.end()
                trace.end()

            # Prepare results
            result = {
                "company_info": company_info,
                "industry_info": industry_info,
                "use_cases": use_cases,
                "resources": resources,
                "markdown": markdown,
                "markdown_path": markdown_path,
                "json_path": json_path,
                "trace_id": trace_id,
            }

            return result

        except Exception as e:
            logger.error(f"Error in use case generation workflow: {e}")
            if self.monitoring_enabled:
                trace.update(error=str(e), status="error")
                trace.end()
            raise
