import asyncio
import json
import os
import time
from typing import Dict, List
import uuid

import matplotlib.pyplot as plt
import pandas as pd
from rich.console import Console
from rich.table import Table
import seaborn as sns
from vertexai.evaluation import EvalTask, PointwiseMetric, constants
from vertexai.generative_models import GenerationConfig, GenerativeModel
import weave


class AgentEvaluator:
    def __init__(
        self,
        model_name: str = "gemini-1.5-pro",
        temperature: float = 0.1,
        verbosity: int = 0,  # 0: minimal, 1: normal, 2: detailed, 3: debug
        use_weave: bool = True,
        project: str = None,
        location: str = "us-central1",
    ):
        # Initialize Vertex AI if project is provided
        if project:
            import vertexai

            vertexai.init(project=project, location=location)

        self.generation_config = GenerationConfig(
            temperature=temperature,
        )
        self.model = GenerativeModel(
            model_name=model_name, generation_config=self.generation_config
        )
        self.verbosity = verbosity
        self.console = Console()
        self.use_weave = use_weave

    def format_dataset_for_eval(self, examples: List[Dict]) -> pd.DataFrame:
        """Convert our dataset format to Vertex AI Eval format"""
        eval_data = []

        for example in examples:
            # Extract expected tool sequence for tool selection evaluation
            expected_tool_sequence = [
                step.get("tool_name", "")
                for step in example["expected_trajectory"]
                if step.get("tool_name") != "python_interpreter"
                or (
                    step.get("tool_name") == "python_interpreter"
                    and any(
                        tool in str(step.get("tool_input", {}))
                        for tool in example["tools_available"]
                        if tool != "python_interpreter"
                    )
                )
            ]

            # Format expected reasoning for each step
            expected_reasoning = "\n".join(
                [
                    f"Step {i+1}: {step.get('reasoning', '')[:200]}..."
                    for i, step in enumerate(example["expected_trajectory"])
                ]
            )

            # Extract expected trajectory details for trajectory evaluation
            expected_trajectory_details = []
            for step in example["expected_trajectory"]:
                step_details = {
                    "tool_name": step.get("tool_name", ""),
                    "tool_input": step.get("tool_input", {}),
                    "reasoning": step.get("reasoning", "")[:200],
                }
                expected_trajectory_details.append(step_details)

            eval_row = {
                "id": f"example_{len(eval_data)}",
                "context": example["input"],
                "prompt": example["input"],
                "reference": example["expected_final_response"],
                "tools_available": json.dumps(example["tools_available"]),
                "expected_tool_sequence": json.dumps(expected_tool_sequence),
                "expected_reasoning": expected_reasoning,
                "expected_trajectory": json.dumps(expected_trajectory_details),
                "validation_criteria": json.dumps(example["validation_criteria"]),
                "difficulty": example["difficulty"],
                "tags": json.dumps(example["tags"]),
            }
            eval_data.append(eval_row)

        return pd.DataFrame(eval_data)

    def define_agent_metrics(self) -> List[PointwiseMetric]:
        """Define custom metrics for agent evaluation"""

        # Tool Selection Accuracy Metric
        tool_selection_prompt = """
        Evaluate how effectively the agent selected and used tools:
        
        User prompt: {context}
        Available tools: {tools_available}
        Expected tool sequence: {expected_tool_sequence}
        Agent's tool usage: {tool_usage}
        
        Score from 1-5 where:
        5: Perfect tool selection with correct arguments and sequence
        4: Correct tools but minor issues with arguments or sequence
        3: Some incorrect tool selections or argument issues
        2: Major issues with tool selection or arguments
        1: Completely incorrect tool usage
        
        Provide score and explanation.
        """

        tool_selection_metric = PointwiseMetric(
            metric="tool_selection_accuracy",
            metric_prompt_template=tool_selection_prompt,
        )

        # Reasoning Quality Metric
        reasoning_prompt = """
        Evaluate the quality of the agent's reasoning:
        
        User prompt: {context}
        Expected reasoning pattern: {expected_reasoning}
        Agent's reasoning: {candidate}
        
        Score from 1-5 where:
        5: Excellent reasoning with clear logic and appropriate steps
        4: Good reasoning with minor logical gaps
        3: Adequate reasoning but some unclear steps
        2: Poor reasoning with major logical flaws
        1: No clear reasoning or completely flawed logic
        
        Provide score and explanation.
        """

        reasoning_metric = PointwiseMetric(
            metric="reasoning_quality", metric_prompt_template=reasoning_prompt
        )

        # Final Response Correctness
        response_prompt = """
        Evaluate the correctness of the agent's final response:
        
        User prompt: {context}
        Expected response: {reference}
        Agent's response: {candidate}
        Validation criteria: {validation_criteria}
        
        Score from 1-5 where:
        5: Perfect response that fully addresses the user's request
        4: Good response with minor omissions or inaccuracies
        3: Adequate response but missing important details
        2: Poor response with major inaccuracies
        1: Completely incorrect or irrelevant response
        
        Provide score and explanation.
        """

        response_metric = PointwiseMetric(
            metric="response_correctness", metric_prompt_template=response_prompt
        )

        # Trajectory Evaluation Metric (New)
        trajectory_prompt = """
        Evaluate how well the agent's trajectory matches the expected trajectory:
        
        User prompt: {context}
        Expected trajectory: {expected_trajectory}
        Agent's trajectory: {agent_trajectory}
        
        Score from 1-5 where:
        5: Perfect match in tool selection, arguments, and reasoning flow
        4: Good match with minor deviations that don't affect outcome
        3: Adequate match but with some significant deviations
        2: Poor match with major deviations from expected trajectory
        1: Completely different trajectory that fails to solve the task
        
        Consider:
        - Did the agent use similar tools in a similar sequence?
        - Did the agent's reasoning follow a similar logical path?
        - Did the agent adapt appropriately when faced with unexpected results?
        
        Provide score and explanation.
        """

        trajectory_metric = PointwiseMetric(
            metric="trajectory_match", metric_prompt_template=trajectory_prompt
        )

        # Combine with built-in metrics (removing groundedness)
        metrics = [
            tool_selection_metric,
            reasoning_metric,
            response_metric,
            trajectory_metric,
            constants.Metric.COHERENCE,
        ]

        return metrics

    def _render_summary_table(
        self, summary_metrics: Dict, include_ratings: bool = True
    ) -> Table:
        """
        Render a summary metrics table with optional ratings.

        Args:
            summary_metrics: Dictionary of metrics and their values
            include_ratings: Whether to include ratings column

        Returns:
            Rich Table object with formatted metrics
        """
        # Create a more detailed summary table
        table = Table(title="Summary Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Score", style="magenta")

        if include_ratings:
            table.add_column("Rating", style="yellow")

        # Add rating interpretation
        def get_rating(score):
            if score >= 4.5:
                return "[bold green]Excellent[/bold green]"
            elif score >= 4.0:
                return "[green]Very Good[/green]"
            elif score >= 3.5:
                return "[blue]Good[/blue]"
            elif score >= 3.0:
                return "[yellow]Satisfactory[/yellow]"
            elif score >= 2.0:
                return "[orange]Needs Improvement[/orange]"
            else:
                return "[red]Poor[/red]"

        # Extract base metrics from the keys
        base_metrics = set()
        for key in summary_metrics.keys():
            parts = key.split("/")
            if len(parts) >= 2 and parts[-1] == "Mean":
                # Extract the base metric name (everything before the last two parts)
                base_metric = "/".join(parts[:-1])
                base_metrics.add(base_metric)

        # Add rows for each base metric (using Mean values)
        for base_metric in sorted(base_metrics):
            mean_key = f"{base_metric}/Mean"
            if mean_key in summary_metrics:
                score = summary_metrics[mean_key]

                # Format the display name
                display_name = base_metric
                if "/score" in display_name:
                    display_name = display_name.replace("/score", "")
                display_name = display_name.replace("_", " ").title()

                if include_ratings:
                    table.add_row(display_name, f"{score:.2f}", get_rating(score))
                else:
                    table.add_row(display_name, f"{score:.2f}")

        # Add Row Count separately
        if "Row Count" in summary_metrics:
            if include_ratings:
                table.add_row("Row Count", f"{summary_metrics['Row Count']:.2f}", "")
            else:
                table.add_row("Row Count", f"{summary_metrics['Row Count']:.2f}")

        return table

    def _render_detailed_metrics_table(self, summary_metrics: Dict) -> Table:
        """
        Render a detailed metrics table with statistics.

        Args:
            summary_metrics: Dictionary of metrics and their values

        Returns:
            Rich Table object with detailed metrics
        """
        # Create detailed metrics table
        table = Table(title="Detailed Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Mean", style="green")
        table.add_column("Std", style="blue")
        table.add_column("Min", style="red")
        table.add_column("Max", style="magenta")

        # Extract base metrics from the keys
        base_metrics = set()
        for key in summary_metrics.keys():
            parts = key.split("/")
            if len(parts) >= 2 and parts[-1] in ["Mean", "Std", "Min", "Max"]:
                # Extract the base metric name (everything before the last part)
                base_metric = "/".join(parts[:-1])
                base_metrics.add(base_metric)

        # Add rows for each base metric
        for base_metric in sorted(base_metrics):
            if base_metric == "Row Count":
                continue  # Skip Row Count in detailed metrics

            mean_key = f"{base_metric}/Mean"
            std_key = f"{base_metric}/Std"
            min_key = f"{base_metric}/Min"
            max_key = f"{base_metric}/Max"

            if all(
                key in summary_metrics for key in [mean_key, std_key, min_key, max_key]
            ):
                # Format the display name
                display_name = base_metric
                if "/score" in display_name:
                    display_name = display_name.replace("/score", "")
                display_name = display_name.replace("_", " ").title()

                table.add_row(
                    display_name,
                    f"{summary_metrics[mean_key]:.2f}",
                    f"{summary_metrics[std_key]:.2f}",
                    f"{summary_metrics[min_key]:.2f}",
                    f"{summary_metrics[max_key]:.2f}",
                )

        return table

    def run_evaluation(
        self,
        agent,
        eval_dataset: pd.DataFrame,
        output_dir: str = "evaluation_results",
        weave_project: str = "agent_evaluation",
    ) -> Dict:
        """
        Run evaluation on the agent using the provided dataset.

        Args:
            agent: The agent object to evaluate (must have memory attribute)
            eval_dataset: DataFrame containing evaluation examples
            output_dir: Directory to save evaluation results
            weave_project: Weave project name for logging

        Returns:
            Dictionary containing evaluation results
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Initialize results dictionary
        results = {
            "examples": [],
            "summary_metrics": {},
            "detailed_metrics": pd.DataFrame(),
        }

        # Create console for rich output
        console = Console()

        # Initialize progress bar
        if self.verbosity >= 1:
            console.rule("[bold cyan]Running Agent on Evaluation Dataset")

        # Define metrics
        metrics = self.define_agent_metrics()

        # Run agent on each example
        for i, row in eval_dataset.iterrows():
            if self.verbosity >= 1:
                console.print(f"Example {i+1}/{len(eval_dataset)}")
                console.print(f"Prompt: {row['prompt']}")

            # Run agent on the prompt
            try:
                # Reset agent memory before each run
                if hasattr(agent, "memory"):
                    agent.memory.reset()

                # Run the agent
                agent_result = agent.run(row["prompt"])

                # Convert function objects to their string representation if needed
                if callable(agent_result):
                    import inspect

                    agent_result = inspect.getsource(agent_result)
                elif not isinstance(agent_result, str):
                    agent_result = str(agent_result)

                # Extract tool usage, reasoning, and trajectory from agent memory
                tool_usage = self._extract_tool_usage_from_memory(agent)
                reasoning = self._extract_reasoning_from_memory(agent)
                trajectory = self._extract_trajectory_from_memory(agent)

                # Store the example result
                example_result = {
                    "id": row["id"],
                    "prompt": row["prompt"],
                    "final_response": agent_result,
                    "tool_usage": json.dumps(tool_usage),  # Convert to JSON string
                    "reasoning": reasoning,
                    "trajectory": trajectory,
                    "memory": agent.memory if hasattr(agent, "memory") else None,
                }
                results["examples"].append(example_result)

                # Add results to dataset for evaluation - one column at a time
                eval_dataset.at[i, "candidate"] = agent_result
                eval_dataset.at[i, "tool_usage"] = json.dumps(
                    tool_usage
                )  # Convert to JSON string
                eval_dataset.at[i, "agent_reasoning"] = reasoning
                eval_dataset.at[i, "agent_trajectory"] = trajectory

                # Log for debugging
                if self.verbosity >= 2:
                    console.print(f"Response: {agent_result}")
                    console.print(f"Extracted tools: {len(tool_usage)}")
                    if self.verbosity >= 3:
                        console.print(f"Tool usage: {tool_usage}")
                        console.print(f"Reasoning: {reasoning[:100]}...")
                        console.print(f"Trajectory: {trajectory[:100]}...")

            except Exception as e:
                if self.verbosity >= 1:
                    console.print(
                        f"[bold red]Error running agent on example {i+1}:[/bold red] {str(e)}"
                    )
                # Set empty values for failed runs - one column at a time
                eval_dataset.at[i, "candidate"] = "Error: " + str(e)
                eval_dataset.at[i, "tool_usage"] = "[]"
                eval_dataset.at[i, "agent_reasoning"] = ""
                eval_dataset.at[i, "agent_trajectory"] = "[]"

                # Store the error in results
                example_result = {
                    "id": row["id"],
                    "prompt": row["prompt"],
                    "final_response": "Error: " + str(e),
                    "tool_usage": "[]",
                    "reasoning": "",
                    "trajectory": "[]",
                    "memory": None,
                }
                results["examples"].append(example_result)

        # Save the dataset with agent outputs
        eval_dataset.to_csv(os.path.join(output_dir, "agent_outputs.csv"), index=False)

        # Run evaluation using Vertex AI Evaluation
        if self.verbosity >= 1:
            console.rule("[bold cyan]Running Vertex AI Evaluation")

        # Print dataset columns for debugging
        if self.verbosity >= 3:
            console.print("Dataset columns for evaluation:")
            console.print(list(eval_dataset.columns))

            # Print sample row for debugging
            console.print("Sample row from evaluation dataset:")
            sample_row = eval_dataset.iloc[0]
            for col in eval_dataset.columns:
                value = str(sample_row[col])
                if len(value) > 100:
                    value = value[:100] + "..."
                console.print(f"{col}: {value}")

        # Run Vertex AI evaluation
        if self.verbosity >= 1:
            self.console.rule("[bold blue]Running Vertex AI Evaluation")

        # Change experiment name to use hyphens instead of underscores and add unique ID
        eval_task = EvalTask(
            dataset=eval_dataset,
            metrics=metrics,
            experiment="agent-evaluation",
        )

        run_id = f"{int(time.time())}-{str(uuid.uuid4())[:8]}"
        if self.verbosity >= 1:
            self.console.print(
                f"[bold blue]Starting evaluation with run ID: [/bold blue][cyan]{run_id}[/cyan]"
            )

        # Run the evaluation
        eval_result = eval_task.evaluate(
            model=self.model,
            experiment_run_name=f"agent-eval-run-{run_id}",
        )

        # Save results and store in results dictionary
        if hasattr(eval_result, "metrics_table") and isinstance(
            eval_result.metrics_table, pd.DataFrame
        ):
            eval_result.metrics_table.to_csv(
                f"{output_dir}/detailed_metrics.csv", index=False
            )
            if self.verbosity >= 1:
                self.console.print(
                    f"[green]✓[/green] Saved detailed metrics to {output_dir}/detailed_metrics.csv"
                )

            # Debug: Print the metrics table columns and a sample row
            if self.verbosity >= 3:
                self.console.print(
                    f"[bold cyan]Metrics table columns:[/bold cyan] {list(eval_result.metrics_table.columns)}"
                )
                if not eval_result.metrics_table.empty:
                    self.console.print("[bold cyan]Sample metrics row:[/bold cyan]")
                    sample_row = eval_result.metrics_table.iloc[0]
                    for col in eval_result.metrics_table.columns:
                        self.console.print(f"  {col}: {sample_row[col]}")

            # Store metrics table in results
            results["detailed_metrics"] = eval_result.metrics_table

            # Calculate summary metrics
            summary_metrics = {}

            # Find score columns - be more flexible with column name patterns
            score_columns = []
            for col in eval_result.metrics_table.columns:
                # Include any column that might contain scores
                if (
                    "score" in col.lower()
                    or "accuracy" in col.lower()
                    or "quality" in col.lower()
                    or "match" in col.lower()
                    or "coherence" in col.lower()
                ):
                    score_columns.append(col)

            if self.verbosity >= 2:
                self.console.print(
                    f"[bold cyan]Found score columns:[/bold cyan] {score_columns}"
                )

            # If no score columns found, try to use numeric columns as fallback
            if not score_columns:
                numeric_cols = eval_result.metrics_table.select_dtypes(
                    include=["number"]
                ).columns.tolist()
                score_columns = [col for col in numeric_cols if col != "id"]
                if self.verbosity >= 1:
                    self.console.print(
                        f"[yellow]No score columns found, using numeric columns:[/yellow] {score_columns}"
                    )

            # Calculate summary statistics
            for col in score_columns:
                try:
                    # Check if column has numeric values
                    if pd.api.types.is_numeric_dtype(eval_result.metrics_table[col]):
                        mean = eval_result.metrics_table[col].mean()
                        std = eval_result.metrics_table[col].std()
                        min_val = eval_result.metrics_table[col].min()
                        max_val = eval_result.metrics_table[col].max()

                        # Add to summary metrics
                        summary_metrics[f"{col}/Mean"] = mean
                        summary_metrics[f"{col}/Std"] = std
                        summary_metrics[f"{col}/Min"] = min_val
                        summary_metrics[f"{col}/Max"] = max_val

                        if self.verbosity >= 2:
                            self.console.print(
                                f"[green]✓[/green] Processed column {col}: mean={mean:.2f}, std={std:.2f}"
                            )
                    elif self.verbosity >= 2:
                        self.console.print(
                            f"[yellow]Skipping non-numeric column: {col}[/yellow]"
                        )
                except Exception as e:
                    if self.verbosity >= 1:
                        self.console.print(
                            f"[red]Error processing column {col}: {str(e)}[/red]"
                        )

            # Add row count as a metric
            summary_metrics["Row Count"] = len(eval_dataset)

            # If no metrics were found, add some dummy metrics for testing
            if len(summary_metrics) <= 1:  # Only Row Count
                if self.verbosity >= 1:
                    self.console.print(
                        "[yellow]Warning: No metrics found in evaluation results. Adding dummy metrics for testing.[/yellow]"
                    )

                # Extract any available metrics from the evaluation result object
                if hasattr(eval_result, "metrics") and self.verbosity >= 2:
                    self.console.print(
                        f"[cyan]Available metrics in eval_result.metrics: {eval_result.metrics}[/cyan]"
                    )

                    # Try to extract metrics from eval_result.metrics
                    if isinstance(eval_result.metrics, dict):
                        for metric_name, metric_value in eval_result.metrics.items():
                            if isinstance(metric_value, (int, float)):
                                summary_metrics[f"{metric_name}/Mean"] = float(
                                    metric_value
                                )
                                summary_metrics[f"{metric_name}/Std"] = 0.0
                                summary_metrics[f"{metric_name}/Min"] = float(
                                    metric_value
                                )
                                summary_metrics[f"{metric_name}/Max"] = float(
                                    metric_value
                                )

                # If still no metrics, add dummy metrics
                if len(summary_metrics) <= 1:
                    for metric in [
                        "tool_selection_accuracy",
                        "reasoning_quality",
                        "response_correctness",
                        "trajectory_match",
                        "coherence",
                    ]:
                        summary_metrics[f"{metric}_score/Mean"] = 0.0
                        summary_metrics[f"{metric}_score/Std"] = 0.0
                        summary_metrics[f"{metric}_score/Min"] = 0.0
                        summary_metrics[f"{metric}_score/Max"] = 0.0

            # Store summary metrics in results
            results["summary_metrics"] = summary_metrics
        else:
            if self.verbosity >= 1:
                self.console.print(
                    "[yellow]Warning: Could not save detailed metrics - metrics_table not available[/yellow]"
                )

            # Check what attributes are available on eval_result
            if self.verbosity >= 2:
                self.console.print(
                    f"[cyan]Available attributes on eval_result: {dir(eval_result)}[/cyan]"
                )

            # Initialize empty summary metrics
            results["summary_metrics"] = {"Row Count": len(eval_dataset)}

        # Generate visualizations
        self._generate_visualizations(eval_result, output_dir)

        # Log to Weave if enabled
        if self.use_weave:
            if self.verbosity >= 1:
                self.console.rule("[bold blue]Logging to Weave")

            # Initialize Weave if not already initialized
            if weave_project:
                try:
                    weave.init(weave_project)
                except Exception as e:
                    if self.verbosity >= 1:
                        self.console.print(
                            f"[yellow]Warning: Could not initialize Weave project: {str(e)}[/yellow]"
                        )

            # Create a lookup dictionary for agent responses
            response_lookup = {
                response["id"]: response for response in results["examples"]
            }

            # Create a lookup dictionary for Vertex AI metrics
            metrics_lookup = {}
            if hasattr(eval_result, "metrics_table") and isinstance(
                eval_result.metrics_table, pd.DataFrame
            ):
                for _, row in eval_result.metrics_table.iterrows():
                    example_id = row.get("id")
                    if example_id:
                        # Extract all metrics from the row
                        metrics = {}
                        for col in eval_result.metrics_table.columns:
                            if "score" in col.lower() and isinstance(
                                row[col], (int, float)
                            ):
                                metrics[col] = float(row[col])

                        metrics_lookup[example_id] = metrics

            # Create a pass-through function that returns pre-computed results
            @weave.op()
            def pass_through_function(id: str, context: str):
                """Return pre-computed agent results and metrics without running the agent again"""
                # Create a dictionary to store the results
                result = {
                    "final_response": "",
                    "tool_usage": [],
                    "reasoning": "",
                    "trajectory": [],
                    "vertex_metrics": {},
                    "steps": [],
                }

                # Find the example with matching ID in results["examples"]
                matching_examples = [ex for ex in results["examples"] if ex["id"] == id]
                if matching_examples:
                    example = matching_examples[0]

                    # Get the agent response
                    result["final_response"] = example.get("final_response", "")

                    # Parse JSON strings back to objects for Weave
                    try:
                        result["tool_usage"] = json.loads(
                            example.get("tool_usage", "[]")
                        )
                    except:
                        result["tool_usage"] = []

                    result["reasoning"] = example.get("reasoning", "")

                    try:
                        result["trajectory"] = json.loads(
                            example.get("trajectory", "[]")
                        )
                    except:
                        result["trajectory"] = []

                    # Get the agent memory if available
                    memory = example.get("memory")

                    # Extract steps from memory if available
                    if memory and hasattr(memory, "steps"):
                        for step in memory.steps:
                            step_info = {"type": str(type(step))}

                            # Extract tool calls
                            if hasattr(step, "tool_calls") and step.tool_calls:
                                step_info["tool_calls"] = [
                                    {"name": tc.name, "arguments": tc.arguments}
                                    for tc in step.tool_calls
                                ]

                            # Extract model output
                            if (
                                hasattr(step, "model_output_message")
                                and step.model_output_message
                            ):
                                step_info["model_output"] = (
                                    step.model_output_message.content
                                )

                            # Extract action output
                            if hasattr(step, "action_output"):
                                step_info["action_output"] = str(step.action_output)

                            result["steps"].append(step_info)

                # Get Vertex AI metrics from lookup if available
                if metrics_lookup and id in metrics_lookup:
                    result["vertex_metrics"] = metrics_lookup.get(id, {})

                return result

            # Create scorers that extract specific information, not just passing through metrics
            @weave.op()
            def tool_selection_scorer(model_output: dict) -> dict:
                """Score tool selection based on tool usage data"""
                if model_output is None:
                    return {"tool_selection": 0.0}

                # Get the Vertex AI score if available
                vertex_metrics = model_output.get("vertex_metrics", {})
                vertex_score = vertex_metrics.get("tool_selection_accuracy/score", 0.0)
                # If vertex_score is a dict, try to get the mean value
                if isinstance(vertex_score, dict):
                    vertex_score = vertex_score.get("mean", 0.0)

                # Get the tool usage data
                tool_usage = model_output.get("tool_usage", [])

                # Extract tool names from steps if available
                steps = model_output.get("steps", [])
                tool_names_from_steps = []

                for step in steps:
                    tool_calls = step.get("tool_calls", [])
                    for tool_call in tool_calls:
                        tool_name = tool_call.get("name")
                        if tool_name:
                            tool_names_from_steps.append(tool_name)

                # Return both the Vertex score and the actual tool usage for analysis
                return {
                    "tool_selection": vertex_score,
                    "tools_used": len(tool_usage) or len(tool_names_from_steps),
                    "tool_names": [
                        t.get("tool_name", "")
                        for t in tool_usage
                        if isinstance(t, dict)
                    ]
                    or tool_names_from_steps,
                }

            @weave.op()
            def response_correctness_scorer(model_output: dict) -> dict:
                """Score response correctness"""
                if model_output is None:
                    return {"response_correctness": 0.0}

                # Get the Vertex AI score if available
                vertex_metrics = model_output.get("vertex_metrics", {})
                vertex_score = vertex_metrics.get("response_correctness/score", 0.0)
                # Fix: Handle the case where the metric is a float or dict
                if isinstance(vertex_score, dict):
                    vertex_score = vertex_score.get("mean", 0.0)

                # Get the response
                response = model_output.get("final_response", "")

                # Return both the score and response length as a simple additional metric
                return {
                    "response_correctness": vertex_score,
                    "response_length": len(response),
                }

            @weave.op()
            def trajectory_analysis_scorer(model_output: dict) -> dict:
                """Analyze the agent's trajectory"""
                if model_output is None:
                    return {"trajectory_match": 0.0}

                # Get the Vertex AI score if available
                vertex_metrics = model_output.get("vertex_metrics", {})
                vertex_score = vertex_metrics.get("trajectory_match/score", 0.0)
                # Fix: Handle the case where the metric is a float or dict
                if isinstance(vertex_score, dict):
                    vertex_score = vertex_score.get("mean", 0.0)

                # Get the trajectory data
                trajectory = model_output.get("trajectory", [])

                # Get steps from memory if available
                steps = model_output.get("steps", [])

                # Return both the score and trajectory analysis
                return {
                    "trajectory_match": vertex_score,
                    "trajectory_steps": len(trajectory) or len(steps),
                    "tools_in_trajectory": len(
                        [
                            step
                            for step in trajectory
                            if isinstance(step, dict) and step.get("tool_name")
                        ]
                    )
                    or len(
                        [
                            step
                            for step in steps
                            if "tool_calls" in step and step["tool_calls"]
                        ]
                    ),
                }

            @weave.op()
            def reasoning_quality_scorer(model_output: dict) -> dict:
                """Score reasoning quality"""
                if model_output is None:
                    return {"reasoning_quality": 0.0}

                # Get the Vertex AI score if available
                vertex_metrics = model_output.get("vertex_metrics", {})
                vertex_score = vertex_metrics.get("reasoning_quality/score", 0.0)
                # Fix: Handle the case where the metric is a float or dict
                if isinstance(vertex_score, dict):
                    vertex_score = vertex_score.get("mean", 0.0)

                # Get the reasoning
                reasoning = model_output.get("reasoning", "")

                # Return both the score and reasoning length as a simple additional metric
                return {
                    "reasoning_quality": vertex_score,
                    "reasoning_length": len(reasoning),
                }

            @weave.op()
            def coherence_scorer(model_output: dict) -> dict:
                """Score coherence"""
                if model_output is None:
                    return {"coherence": 0.0}

                # Get the Vertex AI score if available
                vertex_metrics = model_output.get("vertex_metrics", {})
                vertex_score = vertex_metrics.get("coherence/score", 0.0)
                # Fix: Handle the case where the metric is a float or dict
                if isinstance(vertex_score, dict):
                    vertex_score = vertex_score.get("mean", 0.0)

                # Return the coherence score
                return {"coherence": vertex_score}

            # Prepare examples for Weave evaluation
            weave_examples = []
            for _, row in eval_dataset.iterrows():
                example = {
                    "id": row["id"],
                    "context": row["context"],
                    "reference": row["reference"] if "reference" in row else "",
                }
                weave_examples.append(example)

            # Create Weave evaluation
            evaluation = weave.Evaluation(
                name=f"agent-eval-{run_id}",
                dataset=weave_examples,
                scorers=[
                    tool_selection_scorer,
                    response_correctness_scorer,
                    trajectory_analysis_scorer,
                    reasoning_quality_scorer,
                    coherence_scorer,
                ],
            )

            # Run Weave evaluation with pass-through function
            try:
                # Extract model information
                model_info = "unknown"
                temperature = 0.0  # Default temperature

                if hasattr(agent, "model"):
                    model = agent.model

                    # Extract model name
                    if hasattr(model, "model_id"):
                        model_info = model.model_id
                    elif hasattr(model, "name"):
                        model_info = model.name

                    # Extract temperature
                    if (
                        hasattr(model, "kwargs")
                        and isinstance(model.kwargs, dict)
                        and "temperature" in model.kwargs
                    ):
                        temperature = model.kwargs["temperature"]
                    elif (
                        hasattr(model, "_vertex_model")
                        and hasattr(model._vertex_model, "kwargs")
                        and "temperature" in model._vertex_model.kwargs
                    ):
                        temperature = model._vertex_model.kwargs["temperature"]
                    elif hasattr(model, "temperature"):
                        temperature = model.temperature

                # Get planning_interval and max_steps
                planning_interval = getattr(agent, "planning_interval", 0)
                max_steps = getattr(agent, "max_steps", 0)

                # Create display name
                model_name = (
                    model_info.split("/")[-1]
                    if isinstance(model_info, str) and "/" in model_info
                    else model_info
                )
                display_name = f"Agent-{model_name}-T{temperature}-PI{planning_interval}-Steps{max_steps}"

                weave_results = asyncio.run(
                    evaluation.evaluate(
                        pass_through_function, __weave={"display_name": display_name}
                    )
                )
                if self.verbosity >= 1:
                    self.console.print("[green]✓[/green] Weave evaluation complete")

                # Store Weave run ID
                weave_run_id = (
                    weave_results.run_id if hasattr(weave_results, "run_id") else None
                )
                if self.verbosity >= 1 and weave_run_id:
                    self.console.print(
                        f"[bold]View Weave results at:[/bold] [cyan]https://wandb.ai/{weave_project}/runs/{weave_run_id}[/cyan]"
                    )
            except Exception as e:
                if self.verbosity >= 1:
                    self.console.print(
                        f"[red]Error running Weave evaluation: {str(e)}[/red]"
                    )
                weave_run_id = None
        else:
            weave_run_id = None

        # Return results
        results["weave_run_id"] = weave_run_id
        return results

    def _extract_tool_usage_from_memory(self, agent) -> List[Dict]:
        """Extract tool usage from agent memory"""
        if self.verbosity >= 3:
            print("Debug: Extracting tool usage from memory")

        tools_used = []

        if hasattr(agent, "memory") and hasattr(agent.memory, "steps"):
            from smolagents import ActionStep

            for log in agent.memory.steps:
                if isinstance(log, ActionStep) and log.tool_calls:
                    for tool_call in log.tool_calls:
                        tool_info = {
                            "tool_name": tool_call.name,
                            "tool_args": tool_call.arguments,
                            "tool_output": log.action_output,
                        }
                        tools_used.append(tool_info)

        return tools_used

    def _extract_reasoning_from_memory(self, agent) -> str:
        """Extract reasoning from agent memory"""
        if self.verbosity >= 3:
            print("Debug: Extracting reasoning from memory")

        reasoning = ""

        if hasattr(agent, "memory") and hasattr(agent.memory, "steps"):
            pass

            reasoning_parts = []

            for log in agent.memory.steps:
                if hasattr(log, "model_output_message") and log.model_output_message:
                    reasoning_parts.append(log.model_output_message.content)

            reasoning = "\n\n".join(reasoning_parts)

        return reasoning

    def _extract_trajectory_from_memory(self, agent) -> str:
        """Extract trajectory from agent memory"""
        if self.verbosity >= 3:
            print("Debug: Extracting trajectory from memory")

        trajectory = []

        if hasattr(agent, "memory") and hasattr(agent.memory, "steps"):
            from smolagents import ActionStep

            for i, log in enumerate(agent.memory.steps):
                if isinstance(log, ActionStep) and log.tool_calls:
                    for tool_call in log.tool_calls:
                        step_data = {
                            "step_number": i + 1,
                            "tool_name": tool_call.name,
                            "tool_input": tool_call.arguments,
                            "tool_output": log.action_output,
                            "reasoning": (
                                log.model_output_message.content
                                if log.model_output_message
                                else ""
                            ),
                        }
                        trajectory.append(step_data)

        return json.dumps(trajectory)

    def _generate_visualizations(self, eval_result, output_dir):
        """Generate visualizations from evaluation results"""
        if (
            not hasattr(eval_result, "metrics_table")
            or not isinstance(eval_result.metrics_table, pd.DataFrame)
            or eval_result.metrics_table.empty
        ):
            if self.verbosity >= 1:
                self.console.print(
                    "[yellow]Warning: No metrics data available for visualization[/yellow]"
                )
            return

        metrics_df = eval_result.metrics_table

        # Find score columns - they might have different naming patterns
        score_columns = [col for col in metrics_df.columns if "score" in col.lower()]

        if not score_columns:
            if self.verbosity >= 1:
                self.console.print(
                    "[yellow]Warning: No score columns found in metrics data[/yellow]"
                )
            # Try to use all numeric columns as a fallback
            score_columns = metrics_df.select_dtypes(
                include=["number"]
            ).columns.tolist()
            score_columns = [col for col in score_columns if col != "id"]

        # Create and save summary statistics table
        try:
            # Create summary table data
            table_data = "Evaluation Results Summary\n\n"
            table_data += "Metric      | Mean  | Median | Min   | Max\n"
            table_data += "------------|-------|--------|-------|-------\n"

            # Only display table in console if verbosity level is appropriate
            if self.verbosity >= 1:
                results_table = Table(
                    title="[bold]Evaluation Results Summary[/bold]",
                    show_header=True,
                    header_style="bold cyan",
                )
                results_table.add_column("Metric", style="cyan")
                results_table.add_column("Mean", style="green")
                results_table.add_column("Median", style="blue")
                results_table.add_column("Min", style="red")
                results_table.add_column("Max", style="magenta")

            # Process each metric column
            for col in score_columns:
                try:
                    metric_name = col.replace("_score", "").replace("_", " ").title()
                    mean = metrics_df[col].mean()
                    median = metrics_df[col].median()
                    min_val = metrics_df[col].min()
                    max_val = metrics_df[col].max()

                    # Add to text file data
                    table_data += f"{metric_name:<12} | {mean:.2f} | {median:.2f} | {min_val:.2f} | {max_val:.2f}\n"

                    # Add to console table if appropriate verbosity
                    if self.verbosity >= 1:
                        results_table.add_row(
                            metric_name,
                            f"{mean:.2f}",
                            f"{median:.2f}",
                            f"{min_val:.2f}",
                            f"{max_val:.2f}",
                        )
                except Exception as e:
                    if self.verbosity >= 1:
                        self.console.print(
                            f"[red]Error processing column {col}: {str(e)}[/red]"
                        )

            # Print table to console if appropriate verbosity
            if self.verbosity >= 1:
                self.console.print(results_table)

            # Save table to file
            with open(f"{output_dir}/summary_stats.txt", "w") as f:
                f.write(table_data)

            # Save raw metrics data
            metrics_df.to_csv(f"{output_dir}/raw_metrics.csv", index=False)

            # Generate visualizations
            self._generate_plots(metrics_df, score_columns, output_dir)

        except Exception as e:
            if self.verbosity >= 1:
                self.console.print(
                    f"[red]Error generating summary statistics: {str(e)}[/red]"
                )

    def _generate_plots(self, metrics_df, score_columns, output_dir):
        """Generate visualization plots from metrics data"""
        try:
            # 1. Score distribution plot
            if score_columns:
                plt.figure(figsize=(12, 8))
                plot_data = metrics_df.melt(
                    id_vars=["id"] if "id" in metrics_df.columns else [],
                    value_vars=score_columns,
                    var_name="Metric",
                    value_name="Score",
                )

                if (
                    not plot_data.empty
                    and "Score" in plot_data.columns
                    and plot_data["Score"].notna().any()
                ):
                    sns.boxplot(data=plot_data, x="Metric", y="Score")
                    plt.title("Distribution of Scores by Metric")
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    plt.savefig(f"{output_dir}/score_distribution.png")
                    if self.verbosity >= 1:
                        self.console.print(
                            "[green]✓[/green] Generated score distribution plot"
                        )

            # 2. Difficulty heatmap
            if "difficulty" in metrics_df.columns and score_columns:
                if (
                    len(metrics_df["difficulty"].unique()) > 0
                    and len(score_columns) > 0
                ):
                    plt.figure(figsize=(10, 6))
                    pivot_df = metrics_df.pivot_table(
                        index="difficulty", values=score_columns, aggfunc="mean"
                    )

                    if not pivot_df.empty:
                        sns.heatmap(
                            pivot_df, annot=True, cmap="viridis", vmin=1, vmax=5
                        )
                        plt.title("Average Scores by Difficulty")
                        plt.tight_layout()
                        plt.savefig(f"{output_dir}/difficulty_heatmap.png")

                        if self.verbosity >= 1:
                            self.console.print(
                                "[green]✓[/green] Generated difficulty heatmap"
                            )

                            # Create a rich table for difficulty breakdown
                            difficulty_table = Table(
                                title="[bold]Scores by Difficulty Level[/bold]",
                                show_header=True,
                                header_style="bold cyan",
                            )
                            difficulty_table.add_column("Difficulty", style="cyan")

                            for col in pivot_df.columns:
                                metric_name = (
                                    col.replace("_score", "").replace("_", " ").title()
                                )
                                difficulty_table.add_column(metric_name, style="green")

                            for idx, row in pivot_df.iterrows():
                                values = [f"{row[col]:.2f}" for col in pivot_df.columns]
                                difficulty_table.add_row(str(idx), *values)

                            self.console.print(difficulty_table)

            # 3. Trajectory vs response plot
            if (
                "trajectory_match_score" in metrics_df.columns
                and "response_correctness_score" in metrics_df.columns
            ):
                if (
                    metrics_df["trajectory_match_score"].notna().any()
                    and metrics_df["response_correctness_score"].notna().any()
                ):

                    plt.figure(figsize=(10, 6))
                    plt.scatter(
                        metrics_df["trajectory_match_score"],
                        metrics_df["response_correctness_score"],
                        alpha=0.7,
                    )

                    plt.xlabel("Trajectory Match Score")
                    plt.ylabel("Response Correctness Score")
                    plt.title("Relationship Between Trajectory and Response Quality")
                    plt.grid(True, linestyle="--", alpha=0.7)

                    # Add a diagonal line for reference
                    min_val = min(
                        metrics_df["trajectory_match_score"].min(),
                        metrics_df["response_correctness_score"].min(),
                    )
                    max_val = max(
                        metrics_df["trajectory_match_score"].max(),
                        metrics_df["response_correctness_score"].max(),
                    )
                    plt.plot([min_val, max_val], [min_val, max_val], "k--", alpha=0.5)

                    plt.tight_layout()
                    plt.savefig(f"{output_dir}/trajectory_vs_response.png")

                    if self.verbosity >= 1:
                        self.console.print(
                            "[green]✓[/green] Generated trajectory vs response plot"
                        )

                        # Calculate correlation
                        corr = metrics_df["trajectory_match_score"].corr(
                            metrics_df["response_correctness_score"]
                        )
                        self.console.print(
                            f"[bold]Correlation between trajectory match and response correctness:[/bold] [cyan]{corr:.3f}[/cyan]"
                        )

        except Exception as e:
            if self.verbosity >= 1:
                self.console.print(
                    f"[red]Error generating visualizations: {str(e)}[/red]"
                )


def load_dataset(file_path: str) -> List[Dict]:
    """Load evaluation dataset from JSON file"""
    with open(file_path, "r") as f:
        return json.load(f)


def main():
    console = Console()
    console.rule("[bold magenta]Agent Evaluation Framework")

    # Load generated dataset
    dataset_path = "synthetic_agent_dataset.json"
    console.print(f"[bold blue]Loading dataset from {dataset_path}...")

    try:
        examples = load_dataset(dataset_path)
        console.print(f"[green]✓[/green] Loaded {len(examples)} examples")

        # Display dataset statistics
        tags = {}
        difficulties = {}

        for example in examples:
            for tag in example.get("tags", []):
                tags[tag] = tags.get(tag, 0) + 1

            difficulty = example.get("difficulty", "unknown")
            difficulties[difficulty] = difficulties.get(difficulty, 0) + 1

        # Create dataset stats table
        stats_table = Table(title="Dataset Statistics")
        stats_table.add_column("Category", style="cyan")
        stats_table.add_column("Distribution", style="green")

        # Add difficulty distribution
        difficulty_str = ", ".join([f"{k}: {v}" for k, v in difficulties.items()])
        stats_table.add_row("Difficulties", difficulty_str)

        # Add top tags
        top_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:5]
        tags_str = ", ".join([f"{k}: {v}" for k, v in top_tags])
        stats_table.add_row("Top Tags", tags_str)

        console.print(stats_table)

    except Exception as e:
        console.print(f"[red]Error loading dataset: {str(e)}[/red]")
        return

    # Initialize evaluator with verbosity level
    console.print("[bold blue]Initializing evaluator...")
    evaluator = AgentEvaluator(verbosity=1)  # Default to normal verbosity
    console.print("[green]✓[/green] Evaluator initialized")

    # Format dataset for evaluation
    console.print("[bold blue]Formatting dataset for evaluation...")
    eval_dataset = evaluator.format_dataset_for_eval(examples)
    console.print(
        f"[green]✓[/green] Dataset formatted with {len(eval_dataset)} examples"
    )

    # Import the agent directly instead of creating a function
    try:
        console.print("Importing agent for evaluation...")

        # Import the agent from the specified module
        from customer_support_agent import create_customer_support_agent

        # Create the agent directly
        agent = create_customer_support_agent(
            model_id="google/gemini-1.5-pro",
            use_weave=True,
            temperature=0.2,
            planning_interval=1,
            max_steps=3,
        )

        console.print("✓ Agent imported and ready for evaluation")
    except Exception as e:
        console.print(f"[bold red]Error importing agent:[/bold red] {str(e)}")
        return

    # Run evaluation with the agent object directly
    results = evaluator.run_evaluation(
        agent=agent,
        eval_dataset=eval_dataset,
        output_dir="evaluation_results",
        weave_project="agent_evaluation",
    )

    # Display results summary
    console.rule("[bold green]Evaluation Results")

    # Create summary tables
    console.print("\n[bold]Summary Metrics Table:[/bold]")
    table = evaluator._render_summary_table(results["summary_metrics"])
    console.print(table)

    console.print("\n[bold]Detailed Metrics Table:[/bold]")
    table = evaluator._render_detailed_metrics_table(results["summary_metrics"])
    console.print(table)

    # Display path to results
    console.print("\n[bold green]Evaluation complete![/bold green]")
    console.print(
        "[bold]Detailed results saved to:[/bold] [cyan]evaluation_results/[/cyan]"
    )
    console.print(
        "[bold]Visualizations saved to:[/bold] [cyan]evaluation_results/score_distribution.png[/cyan] and other PNG files"
    )


if __name__ == "__main__":
    main()
