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

    def _safe_end_span(self, span, span_name: str):
        """Safely end a Langfuse span with error handling."""
        if span:
            try:
                span.end()
            except Exception as e:
                logger.error(f"Failed to end Langfuse span '{span_name}': {e}")

    def _safe_end_trace(self, trace, trace_name: str):
        """Safely end a Langfuse trace with error handling."""
        if trace:
            try:
                trace.end()
            except Exception as e:
                logger.error(f"Failed to end Langfuse trace '{trace_name}': {e}")

    async def generate_use_cases(
        self,
        company_name: Optional[str] = None,
        industry_name: Optional[str] = None,
        num_use_cases: int = 5,
    ) -> Dict[str, Any]:
        """Generate AI/Gen AI use cases for a company/industry.

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
            logger.info("Step 1: Researching industry and company")
            research_span = None
            if self.monitoring_enabled and trace:
                try:
                    research_span = trace.span(name="industry_research")
                except Exception as e:
                    logger.error(f"Failed to create Langfuse span: {e}")

            company_info, industry_info = await self.industry_research_agent.research(
                company_name=company_name, industry_name=industry_name
            )

            self._safe_end_span(research_span, "industry_research")

            # Step 2: Generate use cases
            logger.info("Step 2: Generating use cases")
            use_case_span = None
            if self.monitoring_enabled and trace:
                try:
                    use_case_span = trace.span(name="use_case_generation")
                except Exception as e:
                    logger.error(f"Failed to create Langfuse span: {e}")

            use_cases = await self.use_case_generation_agent.generate_use_cases(
                company_info=company_info,
                industry_info=industry_info,
                num_use_cases=num_use_cases,
            )

            self._safe_end_span(use_case_span, "use_case_generation")

            # Step 3: Collect resources
            logger.info("Step 3: Collecting resources")
            resource_span = None
            if self.monitoring_enabled and trace:
                try:
                    resource_span = trace.span(name="resource_collection")
                except Exception as e:
                    logger.error(f"Failed to create Langfuse span: {e}")

            resources = await self.resource_collection_agent.collect_resources(
                use_cases=use_cases
            )

            self._safe_end_span(resource_span, "resource_collection")

            # Step 4: Format results
            logger.info("Step 4: Formatting results")
            document_span = None
            if self.monitoring_enabled and trace:
                try:
                    document_span = trace.span(name="document_generation")
                except Exception as e:
                    logger.error(f"Failed to create Langfuse span: {e}")

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

            self._safe_end_span(document_span, "document_generation")

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

            # End trace successfully
            if self.monitoring_enabled and trace:
                try:
                    trace.update(output={"status": "success", "num_use_cases": len(use_cases)})
                except Exception as e:
                    logger.error(f"Failed to update Langfuse trace: {e}")

            return result

        except Exception as e:
            logger.error(f"Error in use case generation workflow: {e}")
            # Update trace with error information
            if self.monitoring_enabled and trace:
                try:
                    trace.update(output={"status": "error", "error": str(e)})
                except Exception as trace_error:
                    logger.error(f"Failed to update Langfuse trace with error: {trace_error}")
            raise

        finally:
            # Always end the trace in the finally block
            self._safe_end_trace(trace, "use_case_generation")