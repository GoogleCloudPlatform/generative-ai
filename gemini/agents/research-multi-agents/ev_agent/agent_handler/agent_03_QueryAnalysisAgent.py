# @title Helper Functions

from enum import Enum
import json
from typing import List

from google.genai import types
from pydantic import BaseModel
from rich import print as rich_print


class PatternType(str, Enum):
    DISCOVERY = "DISCOVERY"
    COMPARISON = "COMPARISON"
    GAPS = "GAPS"
    PLANNING = "PLANNING"
    ASSESSMENT = "ASSESSMENT"


class OutputType(str, Enum):
    REPORT = "Report"
    TEXT = "Normal Text"
    RAW = "Raw Data"


class QueryEntities(BaseModel):
    pattern_type: PatternType
    cities: List[str]
    states: List[str]
    # research_focus: ResearchFocus
    research_theme: str = "Electric Vehicle"
    output_type: OutputType


# Debug Print Functions with both light and dark theme friendly colors
def print_planning(msg: str):
    rich_print(f"[bold cyan]🤔 PLANNING:[/bold cyan] {msg}")


def print_executing(msg: str):
    rich_print(f"[bold green]⚡ EXECUTING:[/bold green] {msg}")


def print_debug(msg: str):
    rich_print(f"[bold magenta]🔍 DEBUG:[/bold magenta] {msg}")


def print_info(msg: str):
    rich_print(f"[bold yellow]ℹ️ INFO:[/bold yellow] {msg}")


STATE_MAPPING = {
    "New York": "NY",
    "Los Angeles": "CA",
    "Chicago": "IL",
    "Houston": "TX",
    "Phoenix": "AZ",
    "Philadelphia": "PA",
    "San Antonio": "TX",
    "San Diego": "CA",
    "Dallas": "TX",
    "San Jose": "CA",
    "Austin": "TX",
    "Jacksonville": "FL",
    "Fort Worth": "TX",
    "Columbus": "OH",
    "San Francisco": "CA",
}


def extract_query_entities(
    query: str, cities: List[str], pattern_type: str, output_type: str, debug: bool
) -> dict:
    """Extract entities from the query"""
    if debug:
        print_info(f"Extracting entities for cities: {cities}")

    # Validate cities against STATE_MAPPING
    unsupported_cities = [city for city in cities if city not in STATE_MAPPING]
    if unsupported_cities:
        raise ValueError(
            f"Following cities are not supported yet: {', '.join(unsupported_cities)}. Currently supporting only: {', '.join(STATE_MAPPING.keys())}"
        )

    # Map states using the STATE_MAPPING
    states = [STATE_MAPPING[city] for city in cities]
    for city in cities:
        if debug:
            print_info(f"Mapped {city} to state: {STATE_MAPPING[city]}")

    return {
        "pattern_type": pattern_type,
        "cities": cities,
        "states": states,
        "output_type": output_type,
    }


class QueryAnalysisAgent:
    def __init__(self, client, model_name: str):
        self.client = client
        self.model_name = model_name
        self.debug = False

        # Function declaration
        self.function = dict(
            name="extract_query_entities",
            description="Extract entities from EV infrastructure query",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "pattern_type": {
                        "type": "STRING",
                        "enum": [pt.value for pt in PatternType],
                        "description": "Type of analysis pattern",
                    },
                    "cities": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "List of cities mentioned",
                    },
                    "states": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "List of states for the cities",
                    },
                    "output_type": {
                        "type": "STRING",
                        "enum": [ot.value for ot in OutputType],
                        "description": "Type of output requested",
                    },
                },
                "required": ["pattern_type", "cities", "states", "output_type"],
            },
        )

    def _extract_entities(self, query: str) -> QueryEntities:
        if self.debug:
            print_planning("Starting entity extraction...")
            print_debug(f"Processing query: {query}")

        try:
            # First generation for entity extraction
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    {
                        "text": """Examples of patterns:
                        - "I want to understand..." -> DISCOVERY
                        - "Compare between..." -> COMPARISON
                        - "Show gaps in..." -> GAPS
                        - "Where should we add..." -> PLANNING
                        - "How well are... performing" -> ASSESSMENT

                        Now extract entities from this query: """
                        + query
                    }
                ],
                config=types.GenerateContentConfig(
                    tools=[types.Tool(function_declarations=[self.function])]
                ),
            )

            function_call = response.candidates[0].content.parts[0].function_call
            extracted = function_call.args
            if self.debug:
                print_debug(
                    f"Raw extracted entities: {json.dumps(extracted, indent=2)}"
                )

            # Get function response with state mapping
            result = extract_query_entities(
                query=query,
                cities=extracted["cities"],
                pattern_type=extracted["pattern_type"],
                output_type=extracted["output_type"],
                debug=self.debug,
            )

            return QueryEntities(**result)

        except Exception as e:
            if self.debug:
                print_debug(f"Error in entity extraction: {str(e)}")
            raise ValueError(
                f"Could not extract required entities from query. Details: {str(e)}"
            )

    def analyze(self, query: str) -> dict:
        if not self.debug:
            rich_print(
                "[bold yellow]ℹ️ Warning: Deciphering your cryptic commands!  It's like translating ancient hieroglyphs, but with more emojis.  Curious about my interpretations? debug=True reveals all! (And if you want to see the output of each agent stage, set stage_output=True!) 🤔📜 [/bold yellow]"
            )

        if self.debug:
            print_executing("Starting analysis...")

        try:
            # Extract entities
            entities = self._extract_entities(query)
            if self.debug:
                print_planning(f"Found a {entities.pattern_type} pattern! 🎯")

            # Validate cities and states
            if not entities.cities:
                raise ValueError(
                    "No cities mentioned in query. Please specify the city."
                )

            if (
                entities.pattern_type == PatternType.COMPARISON
                and len(entities.cities) < 2
            ):
                raise ValueError(
                    "Comparison requires at least two cities. Please mention both cities."
                )

            if self.debug:
                print_executing(f"Analyzing {', '.join(entities.cities)} 🔄")
                print_info(f"States involved: {', '.join(entities.states)}")

            result = {
                "status": "success",
                "entities": entities.model_dump(),
            }

            if self.debug:
                print_debug("Analysis completed successfully! 🎉")
            return result

        except Exception as e:
            if self.debug:
                print_debug(f"Error in analysis: {str(e)}")
            return {"status": "error", "message": str(e)}
