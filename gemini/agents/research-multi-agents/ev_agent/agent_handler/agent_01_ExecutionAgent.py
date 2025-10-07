# @title Helper Functions

from typing import Any, Dict, Optional, Union

from ev_agent.agent_handler.agent_02_PlanningAgent import *
from ev_agent.agent_handler.agent_04_DataGatherAgent import *
from ev_agent.agent_handler.agent_05_ReportAgent import *
from ev_agent.agent_handler.agent_06_VisualizeAgent import *
from pydantic import BaseModel
from rich import print as rich_print
from termcolor import colored


class ExecutionAgent(BaseModel):
    """🤖 The conductor of our EV infrastructure orchestra!
    Coordinates planning and execution of the analysis pipeline."""

    client: Any
    model_name: str
    api_key: Optional[str] = None
    debug: bool = False
    stage_output: bool = False
    output_type: Optional[str] = None

    def _debug_print(self, message: str, color: str = "blue") -> None:
        """Print colorful debug messages when debug is enabled"""
        if self.debug:
            try:
                print(colored(f"🔍 Debug: {message}", color))
            except:
                # Fallback if termcolor fails
                print(f"🔍 Debug: {message}")

    def _handle_error(self, step: str, error: Exception) -> None:
        """Handle errors with style and grace"""
        error_msg = f"💥 Error in {step}: {str(error)}"
        print(colored(error_msg, "red"))
        if self.debug:
            import traceback

            print(colored(f"📚 Traceback:\n{traceback.format_exc()}", "yellow"))
        raise Exception(error_msg)

    async def execute(self, query: str) -> Union[Dict, str, tuple]:
        """🎭 The main show! Execute the analysis pipeline"""
        try:
            # 🎬 Act 1: Planning Phase
            self._debug_print("🎯 Starting Planning Phase...", "cyan")
            if self.stage_output:
                print("self.stage_output", self.stage_output)
                print("self.debug", self.debug)

            planning_agent = PlanningAgent(
                query=query,
                client=self.client,
                model_name=self.model_name,
                debug=self.debug,
                api_key=self.api_key,
            )
            plan = planning_agent.create_plan()

            if not plan.validated_query.is_valid:
                return {
                    "status": "error",
                    "message": "Invalid query",
                    "suggestions": plan.validated_query.suggestions,
                }

            if self.stage_output:
                rich_print(plan)

            # 🎭 Act 2: Execution Phase
            results = {}
            results["plan"] = plan

            # Scene 1: Query Analysis
            self._debug_print("🔍 Starting Query Analysis...", "green")
            query_agent = QueryAnalysisAgent(self.client, self.model_name)
            results["query_analysis"] = query_agent.analyze(query)
            self.output_type = str(results["query_analysis"]["entities"]["output_type"])

            if self.stage_output:
                print("The Output Type: ", self.output_type)
                rich_print(results["query_analysis"])
                # return results["query_analysis"]

            # Scene 2: Data Gathering
            self._debug_print("📊 Gathering Data...", "green")
            data_agent = DataGatherAgent(
                api_key=self.api_key, radius_miles=100.0, debug=self.debug
            )
            results["data"] = await data_agent.process(results["query_analysis"])

            if self.stage_output:
                rich_print(results["data"])
                # return results["data"]

            # Early return for RAW output type
            if self.output_type == "OutputType.RAW":
                self._debug_print("📦 Returning raw data...", "green")
                return results["data"]

            # Scene 3: Report Generation (if needed)
            if any(step.agent_name == "ReportAgent" for step in plan.steps):
                self._debug_print("📝 Generating Report...", "green")
                report_agent = ReportAgent(
                    client=self.client,
                    model_name=self.model_name,
                    enable_search=plan.enable_search,
                )
                report_result = await report_agent.analyze(
                    results["query_analysis"], results["data"]
                )

                # Handle different output types
                if self.output_type == "OutputType.REPORT":
                    results["report"] = {
                        "combined_report": report_result.combined_report,
                        "citations": report_result.citations_text,
                        "full_text": report_result.full_text,
                        "sections": report_result.sections,
                    }
                elif self.output_type == "OutputType.TEXT":
                    results["report"] = {
                        "citations": report_result.citations_text,
                        "full_text": report_result.full_text,
                        "sections": report_result.sections,
                    }
                    # return report_result.full_text, report_result.citations_text

            # Scene 4: Visualization (if needed)
            if any(step.agent_name == "ChartBuilder" for step in plan.steps):
                self._debug_print("📈 Creating Visualizations...", "green")
                single_city_figs, comparison_figs = plot_all_visualizations(
                    results["data"]
                )
                results["visualizations"] = [single_city_figs, comparison_figs]
                # Display single-city visualizations
                if self.stage_output:
                    if results["visualizations"][0]:
                        print("\n=== Single City Analysis ===")
                        for name, fig in single_city_figs.items():
                            print(f"\nDisplaying: {name.replace('_', ' ').title()}")
                            fig.show()
                    elif results["visualizations"][0]:
                        print("\n=== Multi-City Comparisons ===")
                        for name, fig in comparison_figs.items():
                            print(f"\nDisplaying: {name.replace('_', ' ').title()}")
                            fig.show()

            # 🎬 Final Act: Return Results
            self._debug_print("🎉 Execution Complete!", "cyan")
            return results

        except Exception as e:
            self._handle_error("execution", e)

    @classmethod
    def create(
        cls,
        client: Any,
        model_name: str,
        api_key: Optional[str] = None,
        debug: bool = False,
        stage_output: bool = False,
        output_type: Optional[str] = None,
    ) -> "ExecutionAgent":
        """Factory method for creating an ExecutionAgent"""
        return cls(
            client=client,
            model_name=model_name,
            api_key=api_key,
            debug=debug,
            stage_output=stage_output,
            output_type=output_type,
        )
