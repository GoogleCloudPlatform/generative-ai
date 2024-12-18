# @title Helper Functions

import asyncio
from dataclasses import dataclass
from datetime import datetime
import time
from typing import Dict, List, Optional

from IPython.display import HTML, display
from ev_agent.agent_handler.agent_03_QueryAnalysisAgent import *
from ev_agent.api_handler.api_01_NeighborhoodSummary import *
from ev_agent.api_handler.api_02_EV_Infra_StationAnalysis import *
import nest_asyncio

# Apply nest_asyncio to make async work in Colab
nest_asyncio.apply()


class ColorPrinter:
    """Handle colored output for both Colab light and dark themes."""

    COLORS = {
        "error": "#FF5252",
        "success": "#00C853",
        "info": "#2196F3",
        "warning": "#FFC107",
        "debug": "#7C4DFF",
        "monologue": "#00BCD4",
    }

    @staticmethod
    def print_html(text: str, color: str, bold: bool = False):
        """Print colored text using HTML."""
        style = f"color: {color}; {'font-weight: bold;' if bold else ''}"
        html = f"<span style='{style}'>{text}</span>"
        display(HTML(html))

    @staticmethod
    def print_message(message: str, msg_type: str = "info", bold: bool = False):
        """Print a formatted message with appropriate emoji and color."""
        emojis = {
            "error": "❌",
            "success": "✅",
            "info": "ℹ️",
            "warning": "⚠️",
            "debug": "🔍",
            "monologue": "💭",
        }

        prefix = f"{emojis.get(msg_type, '•')} "
        ColorPrinter.print_html(prefix + message, ColorPrinter.COLORS[msg_type], bold)


@dataclass
class AgentInput:
    pattern_type: PatternType
    cities: List[str]
    states: List[str]
    research_theme: str
    output_type: OutputType


@dataclass
class CityData:
    city: str
    state: str
    summary: Optional[Dict] = None
    ev_data: Optional[Dict] = None
    error: Optional[str] = None

    def to_dict(self):
        return {
            "city": self.city,
            "state": self.state,
            "summary": self.summary,
            "ev_data": self.ev_data,
            "error": self.error,
        }


@dataclass
class DataGatherAgentOutput:
    timestamp: datetime
    cities_data: List[CityData]
    status: str = "success"
    error: Optional[str] = None

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "error": self.error,
            "cities_data": [city for city in self.cities_data],
        }


class DataGatherAgent:
    def __init__(self, api_key: str, radius_miles: float = 100.0, debug: bool = False):
        """Initialize the agent with API configuration."""
        self.api_key = api_key
        self.radius_miles = radius_miles
        self.debug = debug
        self.processor = CitySummaryProcessor()
        self.printer = ColorPrinter()

        if not self.debug:
            rich_print(
                "[bold yellow]ℹ️ Warning: Extracting data from the depths of the internet!  It's a dangerous expedition, fraught with peril... and maybe some cat videos.  Want to see what treasures I unearth? debug=True is your treasure map! (And if you want to see the output of each agent stage, set stage_output=True!) ⛏️🌐 [/bold yellow]"
            )

    def _print_debug(self, message: str, bold: bool = False):
        """Print debug messages if debug is enabled."""
        if self.debug:
            self.printer.print_message(message, "debug", bold)

    def _print_monologue(self, message: str):
        """Print internal monologue messages."""
        self.printer.print_message(message, "monologue", True)

    async def _gather_city_data(self, city: str, state: str) -> CityData:
        """Gather data for a single city using both APIs concurrently."""

        if self.debug:
            self._print_monologue(
                f"Investigating {city}, {state}... *beep boop* Time to multitask!"
            )

        try:
            # Add small delay between cities to prevent rate limiting
            await asyncio.sleep(1)

            # Create tasks for both API calls
            summary_task = asyncio.create_task(self._get_city_summary(city, state))
            ev_task = asyncio.create_task(self._get_ev_data(city, state))

            # Wait for both tasks to complete with timeout
            summary, ev_data = await asyncio.wait_for(
                asyncio.gather(summary_task, ev_task), timeout=300  # 5 minute timeout
            )

            if self.debug:
                self._print_monologue(
                    f"Successfully gathered all data for {city}! *happy robot noises*"
                )

            return CityData(city=city, state=state, summary=summary, ev_data=ev_data)

        except asyncio.TimeoutError:
            error_msg = f"Timeout while gathering data for {city}, {state}"
            if self.debug:
                self.printer.print_message(error_msg, "error")
            return CityData(city=city, state=state, error=error_msg)

        except Exception as e:
            error_msg = f"Error gathering data for {city}, {state}: {str(e)}"
            if self.debug:
                self.printer.print_message(error_msg, "error")
            return CityData(city=city, state=state, error=error_msg)

    async def _get_city_summary(self, city: str, state: str) -> Dict:
        """Get city summary data asynchronously."""
        if self.debug:
            self._print_debug(f"Fetching city summary for {city}, {state}...")

        payload = {
            "city": city,
            "state": state,
            "config": {"categories": "all", "debug": self.debug},
        }

        try:
            summary = await asyncio.to_thread(
                self.processor.create_city_summary, payload
            )

            if self.debug:
                self.printer.print_message(
                    f"Received city summary for {city}", "success"
                )
            return summary

        except Exception as e:
            if self.debug:
                self.printer.print_message(
                    f"Error in city summary for {city}: {str(e)}", "error"
                )
            raise

    async def _get_ev_data(self, city: str, state: str) -> Dict:
        """Get EV charging station data asynchronously."""
        if self.debug:
            self._print_debug(f"Fetching EV data for {city}, {state}...")

        payload = {
            "city": city,
            "state": state,
            "api_key": self.api_key,
            "radius_miles": self.radius_miles,
            "debug": self.debug,
        }

        try:
            # Convert synchronous call to async using asyncio
            result = await asyncio.to_thread(get_charging_stations, payload)

            if self.debug:
                self.printer.print_message(f"Received EV data for {city}", "success")
            return result

        except Exception as e:
            if self.debug:
                self.printer.print_message(
                    f"Error in EV data for {city}: {str(e)}", "error"
                )
            raise

    async def process(self, input_data: Dict) -> DataGatherAgentOutput:
        """Process the input and gather data for all cities."""
        start_time = time.time()
        if self.debug:
            self._print_monologue(
                "Initializing data gathering mission... *whirring sounds*"
            )

        try:
            # Parse input
            agent_input = AgentInput(
                pattern_type=PatternType(input_data["entities"]["pattern_type"]),
                cities=input_data["entities"]["cities"],
                states=input_data["entities"]["states"],
                research_theme=input_data["entities"]["research_theme"],
                output_type=OutputType(input_data["entities"]["output_type"]),
            )

            # Validate input
            if len(agent_input.cities) != len(agent_input.states):
                error_msg = "Number of cities and states must match"
                if self.debug:
                    self.printer.print_message(error_msg, "error", True)
                return DataGatherAgentOutput(
                    timestamp=datetime.now(),
                    cities_data=[],
                    status="error",
                    error=error_msg,
                )

            if self.debug:
                self._print_monologue(
                    f"Processing {len(agent_input.cities)} cities... Time to parallel process!"
                )

            # Create tasks for all cities
            tasks = [
                self._gather_city_data(city, state)
                for city, state in zip(agent_input.cities, agent_input.states)
            ]

            # Gather all results
            cities_data = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out any exceptions and convert to CityData objects
            cities_data = [
                (
                    city
                    if isinstance(city, CityData)
                    else CityData(
                        city=agent_input.cities[i],
                        state=agent_input.states[i],
                        error=str(city),
                    )
                )
                for i, city in enumerate(cities_data)
            ]

            elapsed_time = time.time() - start_time
            if self.debug:
                self._print_monologue(
                    f"Mission accomplished in {elapsed_time:.2f} seconds! *victory beeps*"
                )

            return DataGatherAgentOutput(
                timestamp=datetime.now(), cities_data=cities_data
            )

        except Exception as e:
            error_msg = f"Error in processing: {str(e)}"
            self.printer.print_message(error_msg, "error", True)
            return DataGatherAgentOutput(
                timestamp=datetime.now(),
                cities_data=[],
                status="error",
                error=error_msg,
            )
