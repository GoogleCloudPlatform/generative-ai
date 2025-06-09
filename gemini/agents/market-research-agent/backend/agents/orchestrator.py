import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from langfuse.client import Langfuse
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from config.settings import (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY,
                             MONITORING_CONFIG)
from models.gemini_client import GeminiClient
from models.llm_interface import LLMInterface
from tools.analysis_tools import AnalysisTools
from tools.dataset_tools import DatasetTools
from tools.document_tools import DocumentTools
from tools.search_tools import SearchTools

# Import the workflow creators
from workflows.research_workflow import create_research_workflow
from workflows.use_case_workflow import create_use_case_workflow
from workflows.resource_workflow import create_resource_workflow

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """Type definition for the workflow state."""
    # Input parameters
    company_name: Optional[str]
    industry_name: Optional[str]
    num_use_cases: int
    
    # Research results
    company_info: Dict[str, Any]
    industry_info: Dict[str, Any]
    
    # Use case generation results
    use_cases: List[Dict[str, Any]]
    prioritized_use_cases: List[Dict[str, Any]]
    use_cases_with_keywords: List[Dict[str, Any]]
    
    # Resource collection results
    resources: Dict[str, List[Dict[str, Any]]]
    evaluated_resources: Dict[str, List[Dict[str, Any]]]
    
    # Error tracking
    errors: List[str]
    
    # Monitoring
    trace_id: str


class LangGraphOrchestrator:
    """LangGraph-based orchestrator for coordinating agent workflows."""

    def __init__(self, llm: Optional[LLMInterface] = None):
        """Initialize the orchestrator with LangGraph workflows.

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

        # Create individual workflow functions
        self.research_workflow_func = create_research_workflow(self.llm, self.search_tools)
        self.use_case_workflow_func = create_use_case_workflow(self.llm, self.analysis_tools)
        self.resource_workflow_func = create_resource_workflow(self.llm, self.dataset_tools)

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

        # Build the LangGraph workflow
        self.workflow = self._build_workflow()

    def _safe_span_operation(self, operation, span_name: str, *args, **kwargs):
        """Safely execute span operations with error handling."""
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            logger.error(f"Failed to execute span operation '{span_name}': {e}")
            return None

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Create workflow graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes for each workflow step
        workflow.add_node("research", self._research_node)
        workflow.add_node("use_case_generation", self._use_case_node)
        workflow.add_node("resource_collection", self._resource_node)
        workflow.add_node("document_generation", self._document_node)
        
        # Define the workflow edges
        workflow.set_entry_point("research")
        workflow.add_edge("research", "use_case_generation")
        workflow.add_edge("use_case_generation", "resource_collection")
        workflow.add_edge("resource_collection", "document_generation")
        workflow.add_edge("document_generation", END)
        
        # Add memory for state persistence
        memory = MemorySaver()
        
        return workflow.compile(checkpointer=memory)

    async def _research_node(self, state: WorkflowState) -> WorkflowState:
        """Execute the research workflow node."""
        logger.info("Executing research workflow node")
        
        span = None
        if self.monitoring_enabled and hasattr(self, 'current_trace'):
            span = self._safe_span_operation(
                self.current_trace.span, "research_workflow", name="research_workflow"
            )
        
        try:
            # Execute research workflow
            result = await self.research_workflow_func(dict(state))
            
            # Update state with research results
            state.update({
                "company_info": result.get("company_info", {}),
                "industry_info": result.get("industry_info", {}),
            })
            
            # Add any errors from research
            if "error" in result:
                state.setdefault("errors", []).append(f"Research: {result['error']}")
            
            logger.info("Research workflow node completed successfully")
            return state
            
        except Exception as e:
            error_msg = f"Error in research workflow: {e}"
            logger.error(error_msg)
            state.setdefault("errors", []).append(error_msg)
            return state
            
        finally:
            if span:
                self._safe_span_operation(span.end, "research_workflow")

    async def _use_case_node(self, state: WorkflowState) -> WorkflowState:
        """Execute the use case generation workflow node."""
        logger.info("Executing use case generation workflow node")
        
        span = None
        if self.monitoring_enabled and hasattr(self, 'current_trace'):
            span = self._safe_span_operation(
                self.current_trace.span, "use_case_workflow", name="use_case_workflow"
            )
        
        try:
            # Execute use case workflow
            result = await self.use_case_workflow_func(dict(state))
            
            # Update state with use case results
            state.update({
                "use_cases": result.get("use_cases", []),
                "prioritized_use_cases": result.get("prioritized_use_cases", []),
                "use_cases_with_keywords": result.get("use_cases_with_keywords", []),
            })
            
            # Add any errors from use case generation
            if "error" in result:
                state.setdefault("errors", []).append(f"Use Case Generation: {result['error']}")
            
            logger.info(f"Use case generation completed: {len(state.get('use_cases', []))} use cases generated")
            return state
            
        except Exception as e:
            error_msg = f"Error in use case generation workflow: {e}"
            logger.error(error_msg)
            state.setdefault("errors", []).append(error_msg)
            return state
            
        finally:
            if span:
                self._safe_span_operation(span.end, "use_case_workflow")

    async def _resource_node(self, state: WorkflowState) -> WorkflowState:
        """Execute the resource collection workflow node."""
        logger.info("Executing resource collection workflow node")
        
        span = None
        if self.monitoring_enabled and hasattr(self, 'current_trace'):
            span = self._safe_span_operation(
                self.current_trace.span, "resource_workflow", name="resource_workflow"
            )
        
        try:
            # Execute resource workflow
            result = await self.resource_workflow_func(dict(state))
            
            # Update state with resource results
            state.update({
                "resources": result.get("resources", {}),
                "evaluated_resources": result.get("evaluated_resources", {}),
            })
            
            # Add any errors from resource collection
            if "error" in result:
                state.setdefault("errors", []).append(f"Resource Collection: {result['error']}")
            
            total_resources = sum(len(resources) for resources in state.get("resources", {}).values())
            logger.info(f"Resource collection completed: {total_resources} resources found")
            return state
            
        except Exception as e:
            error_msg = f"Error in resource collection workflow: {e}"
            logger.error(error_msg)
            state.setdefault("errors", []).append(error_msg)
            return state
            
        finally:
            if span:
                self._safe_span_operation(span.end, "resource_workflow")

    async def _document_node(self, state: WorkflowState) -> WorkflowState:
        """Execute the document generation node."""
        logger.info("Executing document generation node")
        
        span = None
        if self.monitoring_enabled and hasattr(self, 'current_trace'):
            span = self._safe_span_operation(
                self.current_trace.span, "document_generation", name="document_generation"
            )
        
        try:
            # Generate documents using document tools
            company_info = state.get("company_info", {})
            industry_info = state.get("industry_info", {})
            use_cases = state.get("use_cases", [])
            resources = state.get("resources", {})
            
            markdown = self.document_tools.format_use_cases_markdown(
                use_cases=use_cases,
                company_info=company_info,
                industry_info=industry_info,
                resources=resources,
            )

            markdown_path = self.document_tools.save_use_cases_markdown(
                markdown=markdown, 
                company_name=state.get("company_name") or state.get("industry_name")
            )

            json_path = self.document_tools.save_use_cases_json(
                use_cases=use_cases,
                company_info=company_info,
                industry_info=industry_info,
                resources=resources,
                company_name=state.get("company_name") or state.get("industry_name"),
            )
            
            # Add document paths to state
            state.update({
                "markdown": markdown,
                "markdown_path": markdown_path,
                "json_path": json_path,
            })
            
            logger.info("Document generation completed successfully")
            return state
            
        except Exception as e:
            error_msg = f"Error in document generation: {e}"
            logger.error(error_msg)
            state.setdefault("errors", []).append(error_msg)
            return state
            
        finally:
            if span:
                self._safe_span_operation(span.end, "document_generation")

    async def generate_use_cases(
        self,
        company_name: Optional[str] = None,
        industry_name: Optional[str] = None,
        num_use_cases: int = 5,
    ) -> Dict[str, Any]:
        """Generate AI/Gen AI use cases using LangGraph workflows.

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
                    name="use_case_generation_langgraph",
                    id=trace_id,
                    metadata={
                        "company_name": company_name,
                        "industry_name": industry_name,
                        "num_use_cases": num_use_cases,
                    },
                )
                self.current_trace = trace
            except Exception as e:
                logger.error(f"Failed to create Langfuse trace: {e}")

        try:
            # Initialize workflow state
            initial_state: WorkflowState = {
                "company_name": company_name,
                "industry_name": industry_name,
                "num_use_cases": num_use_cases,
                "company_info": {},
                "industry_info": {},
                "use_cases": [],
                "prioritized_use_cases": [],
                "use_cases_with_keywords": [],
                "resources": {},
                "evaluated_resources": {},
                "errors": [],
                "trace_id": trace_id,
            }

            # Execute the LangGraph workflow
            logger.info("Starting LangGraph workflow execution")
            
            # Create a unique thread ID for this execution
            thread_id = f"thread_{trace_id}"
            config = {"configurable": {"thread_id": thread_id}}
            
            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state, config=config)

            # Prepare results from final state
            result = {
                "company_info": final_state.get("company_info", {}),
                "industry_info": final_state.get("industry_info", {}),
                "use_cases": final_state.get("use_cases", []),
                "resources": final_state.get("resources", {}),
                "markdown": final_state.get("markdown", ""),
                "markdown_path": final_state.get("markdown_path", ""),
                "json_path": final_state.get("json_path", ""),
                "trace_id": trace_id,
                "workflow_state": final_state,
                "errors": final_state.get("errors", []),
            }

            # End trace successfully
            if self.monitoring_enabled and trace:
                try:
                    trace.update(
                        output={
                            "status": "success", 
                            "num_use_cases": len(final_state.get("use_cases", [])),
                            "workflow_steps_completed": [
                                "research_workflow",
                                "use_case_workflow", 
                                "resource_workflow",
                                "document_generation"
                            ],
                            "errors": final_state.get("errors", [])
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to update Langfuse trace: {e}")

            logger.info("LangGraph workflow execution completed successfully")
            return result

        except Exception as e:
            logger.error(f"Error in LangGraph workflow execution: {e}")
            # Update trace with error information
            if self.monitoring_enabled and trace:
                try:
                    trace.update(output={"status": "error", "error": str(e)})
                except Exception as trace_error:
                    logger.error(f"Failed to update Langfuse trace with error: {trace_error}")
            raise

        finally:
            # Clean up trace reference
            if hasattr(self, 'current_trace'):
                delattr(self, 'current_trace')
            
            # Always end the trace in the finally block
            if self.monitoring_enabled and trace:
                try:
                    trace.end()
                except Exception as e:
                    logger.error(f"Failed to end Langfuse trace: {e}")

    def get_workflow_graph(self) -> str:
        """Get a visual representation of the workflow graph."""
        try:
            return self.workflow.get_graph().draw_mermaid()
        except Exception as e:
            logger.error(f"Failed to generate workflow graph: {e}")
            return "Error generating workflow graph"


# For backward compatibility, create an alias
Orchestrator = LangGraphOrchestrator