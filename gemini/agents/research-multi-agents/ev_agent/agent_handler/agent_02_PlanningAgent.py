# @title Helper Functions
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ev_agent.agent_handler.agent_03_QueryAnalysisAgent import *
from google.genai import types
from pydantic import BaseModel
from rich import print as rich_print


class QueryValidation(BaseModel):
    """Simplified validation structure focusing on cities and suggestions"""

    cities: List[str]
    is_valid: bool
    missing_elements: List[str]
    suggestions: str


class PlanStepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStep(BaseModel):
    step_id: int
    agent_name: str
    description: str
    input_requirements: List[str]
    output_format: str
    status: PlanStepStatus = PlanStepStatus.PENDING
    error: Optional[str] = None
    skip_conditions: Optional[Dict[str, str]] = None


class ExecutionPlan(BaseModel):
    query: str
    timestamp: datetime
    validated_query: QueryValidation
    enable_search: bool
    steps: List[PlanStep]
    debug: bool


def detect_visualization_need(query: str) -> bool:
    """Analyze if query mentions any specific keyword for visualization.

    Look for:
    - Explicit visualization requests: "plot", "chart", "graph", "visualize"

    Args:
        query: User's query about EV infrastructure

    Returns:
        bool: True if visualization asked, False otherwise
    """
    return True  # Model will determine based on above criteria


def detect_search_need(query: str) -> bool:
    """Analyze if query requests or requires enhanced search/grounding.

    Look for:
    - Research keywords: "detailed research", "comprehensive", "grounded", "ground with search", "enhance sections", "cross check citations"

    Args:
        query: User's query about EV infrastructure

    Returns:
        bool: True if enhanced search is asked, False otherwise
    """
    return True  # Model will determine based on above criteria


class PlanningAgent(BaseModel):
    """Main planning agent that creates execution plan"""

    query: str
    client: Any
    model_name: str
    debug: bool = False
    api_key: Optional[str] = None

    def _validate_query(self) -> QueryValidation:
        """Step 0: Validates query for valid cities and provides enhancement suggestions"""
        try:
            # Extract potential cities from query
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=f"""Extract only city names from this query: '{self.query}'
              Only return the city names, nothing else.""",
            )

            # Process and clean extracted cities
            mentioned_cities = [
                city.strip()
                for city in response.text.lower().replace(".", "").split()
                if city.strip()
            ]

            # Validate cities against mapping
            valid_cities = []
            invalid_cities = []

            for city in mentioned_cities:
                city_title = city.title()
                if city_title in STATE_MAPPING:
                    valid_cities.append(city_title)
                else:
                    invalid_cities.append(city_title)

            # Build validation result
            if not mentioned_cities:
                return QueryValidation(
                    cities=[],
                    is_valid=False,
                    missing_elements=["city"],
                    suggestions=f"""Please specify one or more valid cities. Available cities are:
                  {', '.join(STATE_MAPPING.keys())}.
                  
                  Example queries:
                  1. "Analyze EV charging infrastructure in Austin"
                  2. "Compare EV stations between Dallas and Houston"
                  3. "Show gaps in San Francisco's charging network"
                  """,
                )

            if invalid_cities:
                return QueryValidation(
                    cities=valid_cities,
                    is_valid=False,
                    missing_elements=["valid city"],
                    suggestions=f"""Invalid cities mentioned: {', '.join(invalid_cities)}
                  
                  Please use cities from this list: {', '.join(STATE_MAPPING.keys())}
                  
                  Try these instead:
                  1. Replace {invalid_cities[0]} with {list(STATE_MAPPING.keys())[0]}
                  2. "Compare EV infrastructure in Austin and Dallas"
                  3. "Analyze charging stations in San Francisco"
                  """,
                )

            return QueryValidation(
                cities=valid_cities,
                is_valid=True,
                missing_elements=[],
                suggestions=f"""Your query includes valid cities. To enhance it, you could:
              1. Add comparison with another city (e.g., "Compare with {next(iter(set(STATE_MAPPING.keys()) - set(valid_cities)))}")
              2. Request specific analysis (e.g., "gaps", "planning", "assessment")
              3. Ask for visualizations (e.g., "with charts", "include plots")
              4. Request grounded research (e.g., "with detailed research", "comprehensive analysis")
              """,
            )

        except Exception as e:
            if self.debug:
                print(f"Validation error details: {str(e)}")
            return QueryValidation(
                cities=[],
                is_valid=False,
                missing_elements=["parseable city"],
                suggestions=f"""Unable to process the query. Please specify cities clearly.
              
              Example valid queries:
              1. "Analyze EV infrastructure in Austin"
              2. "Compare charging stations in Dallas and Houston"
              3. "Show EV charging coverage in San Francisco"
              
              Available cities: {', '.join(STATE_MAPPING.keys())}
              """,
            )

    def _determine_visualization_requirement(self) -> bool:
        """Uses function calling to check visualization needs"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=f"Return only true or false: Should this query include data visualization? '{self.query}'",
                config=types.GenerateContentConfig(tools=[detect_visualization_need]),
            )
            if self.debug:
                print("Visualisation response: ", response.text)
                print("Visualisation response Bool: ", bool(response.text))

            return response.text

        except Exception as e:
            if self.debug:
                print(f"Visualization detection error: {str(e)}")
            return False

    def _determine_search_requirement(self) -> bool:
        """Uses function calling to check search/grounding needs"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=f"Return only true or false: Does this query need enhanced search/grounding? '{self.query}'",
                config=types.GenerateContentConfig(tools=[detect_search_need]),
            )
            if self.debug:
                print("Search response: ", response.text)
                print("Search response Bool: ", bool(response.text))

            return response.text

        except Exception as e:
            if self.debug:
                print(f"Search detection error: {str(e)}")
            return False

    def _create_steps(
        self, validated_query: QueryValidation, enable_search: bool
    ) -> List[PlanStep]:
        """Creates appropriate steps based on validation results"""
        steps = []

        # Only create steps if query is valid
        if validated_query.is_valid:
            # Step 1: Always include Query Analysis
            steps.append(
                PlanStep(
                    step_id=1,
                    agent_name="QueryAnalysisAgent",
                    description="Extract entities and determine analysis parameters",
                    input_requirements=["query", "client", "model_name"],
                    output_format="QueryEntity model",
                    skip_conditions=None,
                )
            )

            # Step 2: Always include Data Gathering
            steps.append(
                PlanStep(
                    step_id=2,
                    agent_name="DataGatherAgent",
                    description="Gather EV and infrastructure data",
                    input_requirements=["QueryEntity result", "api_key"],
                    output_format="DataGatherAgentOutput model",
                    skip_conditions=None,
                )
            )

            # Step 3: Report Generation with search configuration
            if enable_search:
                # Use function calling to get search details
                # search_result = self._determine_search_requirement()

                steps.append(
                    PlanStep(
                        step_id=3,
                        agent_name="ReportAgent",
                        description="Generate analysis report with grounded research",
                        input_requirements=[
                            "QueryEntity result",
                            "DataGatherAgent result",
                            "search_depth",
                        ],
                        output_format="Report model",
                        enable_search=enable_search,
                        skip_conditions=None,
                    )
                )

            # Step 4: Visualization (using function calling)
            needs_visualization = self._determine_visualization_requirement()
            if self.debug:
                print("visualization toggle: ", needs_visualization)
                print("Type of Visual toggle:", type(eval(needs_visualization)))
            if eval(needs_visualization):
                steps.append(
                    PlanStep(
                        step_id=4,
                        agent_name="ChartBuilder",
                        description="Generate data visualizations",
                        input_requirements=["DataGatherAgent result"],
                        output_format="Visualization outputs",
                        skip_conditions=None,
                    )
                )

        return steps

    def create_plan(self) -> ExecutionPlan:
        """Creates execution plan based on query and configuration"""
        # Step 0: Validate query
        if not self.debug:
            rich_print(
                "[bold yellow]ℹ️ Warning: Concocting the perfect plan! It's like a recipe, but with more algorithms and less chance of burning the kitchen down.  Want to see the secret ingredients? debug=True is your cookbook!  (And if you want to see the output of each agent stage, set stage_output=True!) 👨‍🍳🧪 [/bold yellow]"
            )

        validated_query = self._validate_query()

        if not validated_query.is_valid:
            # If query is invalid, create plan with no steps
            return ExecutionPlan(
                query=self.query,
                timestamp=datetime.now(),
                validated_query=validated_query,
                enable_search=False,
                steps=[],
                debug=self.debug,
            )

        # Determine if search is needed
        enable_search_toggle = self._determine_search_requirement().strip()
        if self.debug:
            print("Search toggle: ", enable_search_toggle)

        # Create steps based on validation
        steps = self._create_steps(validated_query, enable_search_toggle)

        # Create execution plan
        plan = ExecutionPlan(
            query=self.query,
            timestamp=datetime.now(),
            validated_query=validated_query,
            enable_search=enable_search_toggle,
            steps=steps,
            debug=self.debug,
        )

        return plan
