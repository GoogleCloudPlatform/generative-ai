from typing import Dict, List, Any, Optional, Union
import pandas as pd
from vertexai.generative_models import GenerativeModel, GenerationConfig
from vertexai.evaluation import (
    EvalTask, 
    PointwiseMetric,
    PointwiseMetricPromptTemplate,
    constants
)
import json
import os
from rich.console import Console
from rich.table import Table
import matplotlib.pyplot as plt
import seaborn as sns
import time
import uuid

class AgentEvaluator:
    def __init__(
        self,
        model_name: str = "gemini-1.5-pro",
        temperature: float = 0.1,
        debug: bool = False
    ):
        self.generation_config = GenerationConfig(
            temperature=temperature,
        )
        self.model = GenerativeModel(
            model_name=model_name,
            generation_config=self.generation_config
        )
        self.debug = debug
        self.console = Console()

    def format_dataset_for_eval(self, examples: List[Dict]) -> pd.DataFrame:
        """Convert our dataset format to Vertex AI Eval format"""
        eval_data = []
        
        for example in examples:
            # Extract expected tool sequence for tool selection evaluation
            expected_tool_sequence = [
                step.get("tool_name", "") 
                for step in example["expected_trajectory"]
                if step.get("tool_name") != "python_interpreter" or 
                   (step.get("tool_name") == "python_interpreter" and 
                    any(tool in str(step.get("tool_input", {})) for tool in example["tools_available"] 
                        if tool != "python_interpreter"))
            ]
            
            # Format expected reasoning for each step
            expected_reasoning = "\n".join([
                f"Step {i+1}: {step.get('reasoning', '')[:200]}..." 
                for i, step in enumerate(example["expected_trajectory"])
            ])
            
            # Extract expected trajectory details for trajectory evaluation
            expected_trajectory_details = []
            for step in example["expected_trajectory"]:
                step_details = {
                    "tool_name": step.get("tool_name", ""),
                    "tool_input": step.get("tool_input", {}),
                    "reasoning": step.get("reasoning", "")[:200]
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
                "tags": json.dumps(example["tags"])
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
        Agent's tool usage: {candidate}
        
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
            metric_prompt_template=tool_selection_prompt
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
            metric="reasoning_quality",
            metric_prompt_template=reasoning_prompt
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
            metric="response_correctness",
            metric_prompt_template=response_prompt
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
            metric="trajectory_match",
            metric_prompt_template=trajectory_prompt
        )

        # Combine with built-in metrics
        metrics = [
            tool_selection_metric,
            reasoning_metric,
            response_metric,
            trajectory_metric,  # Added new trajectory metric
            constants.Metric.GROUNDEDNESS,
            constants.Metric.COHERENCE
        ]
        
        return metrics

    def run_evaluation(self, agent_function, eval_dataset: pd.DataFrame, 
                       output_dir: str = "evaluation_results") -> Dict:
        """Run full evaluation using Vertex AI"""
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Run agent on each example to get responses
        self.console.rule("[bold blue]Running Agent on Evaluation Dataset")
        
        agent_responses = []
        for i, row in eval_dataset.iterrows():
            if self.debug:
                self.console.print(f"[cyan]Example {i+1}/{len(eval_dataset)}[/cyan]")
                self.console.print(f"Prompt: {row['context']}")
            
            # Run agent on the prompt
            try:
                agent_result = agent_function(row['context'])
                
                # Extract tool usage and reasoning from agent result
                tool_usage = self._extract_tool_usage(agent_result)
                reasoning = self._extract_reasoning(agent_result)
                
                # Extract full trajectory for trajectory evaluation
                trajectory = self._extract_trajectory(agent_result)
                
                agent_responses.append({
                    "id": row["id"],
                    "final_response": agent_result if isinstance(agent_result, str) else str(agent_result),
                    "tool_usage": tool_usage,
                    "reasoning": reasoning,
                    "trajectory": trajectory
                })
                
                if self.debug:
                    self.console.print(f"[green]Response:[/green] {agent_result}")
            except Exception as e:
                self.console.print(f"[red]Error running agent on example {i+1}: {str(e)}[/red]")
                agent_responses.append({
                    "id": row["id"],
                    "final_response": f"ERROR: {str(e)}",
                    "tool_usage": "[]",
                    "reasoning": "",
                    "trajectory": "[]"
                })
        
        # Add agent responses to the dataset
        for response in agent_responses:
            mask = eval_dataset["id"] == response["id"]
            eval_dataset.loc[mask, "candidate"] = response["final_response"]
            eval_dataset.loc[mask, "tool_usage"] = response["tool_usage"]
            eval_dataset.loc[mask, "agent_reasoning"] = response["reasoning"]
            eval_dataset.loc[mask, "agent_trajectory"] = response["trajectory"]
        
        # Save the dataset with agent responses
        eval_dataset.to_csv(f"{output_dir}/agent_responses.csv", index=False)
        
        # Define metrics
        metrics = self.define_agent_metrics()
        
        # Run evaluation
        self.console.rule("[bold blue]Running Evaluation")
        
        # Generate a unique run ID using timestamp
        unique_id = f"{int(time.time())}-{str(uuid.uuid4())[:8]}"
        
        # Debug: Print dataset columns and sample rows
        if self.debug:
            self.console.print("[bold cyan]Dataset columns for evaluation:[/bold cyan]")
            self.console.print(list(eval_dataset.columns))
            
            self.console.print("[bold cyan]Sample row from evaluation dataset:[/bold cyan]")
            sample_row = eval_dataset.iloc[0].to_dict()
            for k, v in sample_row.items():
                if isinstance(v, str) and len(v) > 100:
                    self.console.print(f"[cyan]{k}:[/cyan] {v[:100]}...")
                else:
                    self.console.print(f"[cyan]{k}:[/cyan] {v}")
        
        # Change experiment name to use hyphens instead of underscores and add unique ID
        eval_task = EvalTask(
            dataset=eval_dataset,
            metrics=metrics,
            experiment="agent-evaluation",
        )
        
        self.console.print(f"[bold blue]Starting evaluation with run ID: [/bold blue][cyan]{unique_id}[/cyan]")
        
        # Run the evaluation
        eval_result = eval_task.evaluate(
            model=self.model,
            experiment_run_name=f"agent-eval-run-{unique_id}",
        )
        
        # Debug: Inspect evaluation result structure
        if self.debug:
            self.console.rule("[bold magenta]Evaluation Result Structure")
            
            # Check what attributes are available on eval_result
            self.console.print("[bold cyan]Available attributes on eval_result:[/bold cyan]")
            for attr in dir(eval_result):
                if not attr.startswith('_'):
                    self.console.print(f"[cyan]{attr}[/cyan]")
            
            # Print summary metrics
            self.console.print("[bold cyan]Summary metrics:[/bold cyan]")
            if hasattr(eval_result, 'summary_metrics'):
                for metric, value in eval_result.summary_metrics.items():
                    self.console.print(f"[green]{metric}:[/green] {value}")
            else:
                self.console.print("[yellow]No summary_metrics attribute found[/yellow]")
            
            # Check metrics table structure
            self.console.print("[bold cyan]Metrics table info:[/bold cyan]")
            if hasattr(eval_result, 'metrics_table'):
                if isinstance(eval_result.metrics_table, pd.DataFrame):
                    self.console.print(f"Shape: {eval_result.metrics_table.shape}")
                    self.console.print(f"Columns: {list(eval_result.metrics_table.columns)}")
                    self.console.print(f"Sample data (first row):")
                    if not eval_result.metrics_table.empty:
                        sample = eval_result.metrics_table.iloc[0].to_dict()
                        for k, v in sample.items():
                            if isinstance(v, str) and len(v) > 100:
                                self.console.print(f"[green]{k}:[/green] {v[:100]}...")
                            else:
                                self.console.print(f"[green]{k}:[/green] {v}")
                    else:
                        self.console.print("[yellow]Metrics table is empty[/yellow]")
                else:
                    self.console.print(f"[yellow]metrics_table is not a DataFrame: {type(eval_result.metrics_table)}[/yellow]")
            else:
                self.console.print("[yellow]No metrics_table attribute found[/yellow]")
        
        # Save results
        if hasattr(eval_result, 'metrics_table') and isinstance(eval_result.metrics_table, pd.DataFrame):
            eval_result.metrics_table.to_csv(f"{output_dir}/detailed_metrics.csv", index=False)
            self.console.print(f"[green]✓[/green] Saved detailed metrics to {output_dir}/detailed_metrics.csv")
        else:
            self.console.print("[yellow]Warning: Could not save detailed metrics - metrics_table not available[/yellow]")
        
        # Generate visualizations
        self._generate_visualizations(eval_result, output_dir)
        
        # Return results
        return {
            "summary_metrics": eval_result.summary_metrics if hasattr(eval_result, 'summary_metrics') else {},
            "detailed_metrics": eval_result.metrics_table if hasattr(eval_result, 'metrics_table') else pd.DataFrame()
        }
    
    def _extract_tool_usage(self, agent_result) -> str:
        """Extract tool usage from agent result - customize based on your agent's output format"""
        # This is a placeholder - implement based on your agent's output format
        if hasattr(agent_result, "steps"):
            # If agent_result has a steps attribute, extract tool names
            tool_calls = []
            for step in agent_result.steps:
                if hasattr(step, "tool_name") and step.tool_name:
                    tool_calls.append({"tool": step.tool_name})
            return json.dumps(tool_calls)
        return "[]"
    
    def _extract_reasoning(self, agent_result) -> str:
        """Extract reasoning from agent result - customize based on your agent's output format"""
        # This is a placeholder - implement based on your agent's output format
        if hasattr(agent_result, "steps"):
            # If agent_result has a steps attribute, extract reasoning
            reasoning = []
            for i, step in enumerate(agent_result.steps):
                if hasattr(step, "llm_response") and step.llm_response:
                    reasoning.append(f"Step {i+1}: {step.llm_response}")
            return "\n".join(reasoning)
        return ""
    
    def _extract_trajectory(self, agent_result) -> str:
        """Extract full trajectory from agent result - customize based on your agent's output format"""
        # This is a placeholder - implement based on your agent's output format
        if hasattr(agent_result, "steps"):
            # If agent_result has a steps attribute, extract full trajectory
            trajectory = []
            for i, step in enumerate(agent_result.steps):
                step_info = {
                    "step_number": i + 1,
                    "tool_name": getattr(step, "tool_name", None),
                    "tool_input": getattr(step, "tool_args", None),
                    "tool_output": getattr(step, "tool_output", None),
                    "reasoning": getattr(step, "llm_response", "")
                }
                trajectory.append(step_info)
            return json.dumps(trajectory)
        return "[]"
    
    def _generate_visualizations(self, eval_result, output_dir):
        """Generate visualizations from evaluation results"""
        metrics_df = eval_result.metrics_table
        
        # Check if metrics_df is empty
        if metrics_df.empty:
            self.console.print("[yellow]Warning: No metrics data available for visualization[/yellow]")
            return
        
        # Log the available columns for debugging
        self.console.print(f"[cyan]Available metrics columns: {list(metrics_df.columns)}[/cyan]")
        
        # Create rich table for console display
        results_table = Table(title="[bold]Evaluation Results Summary[/bold]", show_header=True, header_style="bold cyan")
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Mean", style="green")
        results_table.add_column("Median", style="blue")
        results_table.add_column("Min", style="red")
        results_table.add_column("Max", style="magenta")
        
        # Find score columns - they might have different naming patterns
        score_columns = [col for col in metrics_df.columns if 'score' in col.lower()]
        
        if not score_columns:
            self.console.print("[yellow]Warning: No score columns found in metrics data[/yellow]")
            # Try to use all numeric columns as a fallback
            score_columns = metrics_df.select_dtypes(include=['number']).columns.tolist()
        
        # Add rows for each metric
        for col in score_columns:
            try:
                metric_name = col.replace('_score', '').replace('_', ' ').title()
                mean = metrics_df[col].mean()
                median = metrics_df[col].median()
                min_val = metrics_df[col].min()
                max_val = metrics_df[col].max()
                results_table.add_row(
                    metric_name,
                    f"{mean:.2f}",
                    f"{median:.2f}",
                    f"{min_val:.2f}",
                    f"{max_val:.2f}"
                )
            except Exception as e:
                self.console.print(f"[red]Error processing column {col}: {str(e)}[/red]")
        
        # Print the table to console
        self.console.print(results_table)
        
        # Save the table as text - using a proper string representation
        with open(f"{output_dir}/summary_stats.txt", "w") as f:
            # Create a string representation of the table data
            table_data = "Evaluation Results Summary\n\n"
            table_data += "Metric      | Mean  | Median | Min   | Max\n"
            table_data += "------------|-------|--------|-------|-------\n"
            
            for col in score_columns:
                try:
                    metric_name = col.replace('_score', '').replace('_', ' ').title()
                    mean = metrics_df[col].mean()
                    median = metrics_df[col].median()
                    min_val = metrics_df[col].min()
                    max_val = metrics_df[col].max()
                    
                    table_data += f"{metric_name:<12} | {mean:.2f} | {median:.2f} | {min_val:.2f} | {max_val:.2f}\n"
                except Exception as e:
                    table_data += f"{col} - Error: {str(e)}\n"
            
            f.write(table_data)
        
        # Save raw metrics data for inspection
        metrics_df.to_csv(f"{output_dir}/raw_metrics.csv", index=False)
        
        try:
            # Set up the figure
            plt.figure(figsize=(12, 8))
            
            if score_columns:
                # Create a boxplot of scores by metric
                plot_data = metrics_df.melt(
                    id_vars=['id'] if 'id' in metrics_df.columns else [], 
                    value_vars=score_columns,
                    var_name='Metric',
                    value_name='Score'
                )
                
                # Check if plot_data has values
                if not plot_data.empty and 'Score' in plot_data.columns and plot_data['Score'].notna().any():
                    sns.boxplot(data=plot_data, x='Metric', y='Score')
                    plt.title('Distribution of Scores by Metric')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    plt.savefig(f"{output_dir}/score_distribution.png")
                    self.console.print(f"[green]✓[/green] Generated score distribution plot")
                else:
                    self.console.print("[yellow]Warning: Not enough data for score distribution plot[/yellow]")
            
            # Create a heatmap of scores by difficulty
            if 'difficulty' in metrics_df.columns and score_columns:
                plt.figure(figsize=(10, 6))
                
                # Check if we have enough data for a pivot table
                if len(metrics_df['difficulty'].unique()) > 0 and len(score_columns) > 0:
                    try:
                        pivot_df = metrics_df.pivot_table(
                            index='difficulty',
                            values=score_columns,
                            aggfunc='mean'
                        )
                        
                        if not pivot_df.empty:
                            sns.heatmap(pivot_df, annot=True, cmap='viridis', vmin=1, vmax=5)
                            plt.title('Average Scores by Difficulty')
                            plt.tight_layout()
                            plt.savefig(f"{output_dir}/difficulty_heatmap.png")
                            self.console.print(f"[green]✓[/green] Generated difficulty heatmap")
                            
                            # Create a rich table for difficulty breakdown
                            difficulty_table = Table(title="[bold]Scores by Difficulty Level[/bold]", show_header=True, header_style="bold cyan")
                            difficulty_table.add_column("Difficulty", style="cyan")
                            
                            for col in pivot_df.columns:
                                metric_name = col.replace('_score', '').replace('_', ' ').title()
                                difficulty_table.add_column(metric_name, style="green")
                            
                            for idx, row in pivot_df.iterrows():
                                values = [f"{row[col]:.2f}" for col in pivot_df.columns]
                                difficulty_table.add_row(str(idx), *values)
                            
                            self.console.print(difficulty_table)
                    except Exception as e:
                        self.console.print(f"[red]Error creating difficulty heatmap: {str(e)}[/red]")
            
            # Add trajectory evaluation visualization
            if 'trajectory_match_score' in metrics_df.columns and 'response_correctness_score' in metrics_df.columns:
                plt.figure(figsize=(10, 6))
                
                # Check if we have valid data for both metrics
                if (metrics_df['trajectory_match_score'].notna().any() and 
                    metrics_df['response_correctness_score'].notna().any()):
                    
                    plt.scatter(
                        metrics_df['trajectory_match_score'], 
                        metrics_df['response_correctness_score'],
                        alpha=0.7
                    )
                    
                    plt.xlabel('Trajectory Match Score')
                    plt.ylabel('Response Correctness Score')
                    plt.title('Relationship Between Trajectory and Response Quality')
                    plt.grid(True, linestyle='--', alpha=0.7)
                    
                    # Add a diagonal line for reference
                    min_val = min(metrics_df['trajectory_match_score'].min(), 
                                  metrics_df['response_correctness_score'].min())
                    max_val = max(metrics_df['trajectory_match_score'].max(), 
                                  metrics_df['response_correctness_score'].max())
                    plt.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5)
                    
                    plt.tight_layout()
                    plt.savefig(f"{output_dir}/trajectory_vs_response.png")
                    self.console.print(f"[green]✓[/green] Generated trajectory vs response plot")
                    
                    # Calculate correlation
                    corr = metrics_df['trajectory_match_score'].corr(metrics_df['response_correctness_score'])
                    self.console.print(f"[bold]Correlation between trajectory match and response correctness:[/bold] [cyan]{corr:.3f}[/cyan]")
        except Exception as e:
            self.console.print(f"[red]Error generating visualizations: {str(e)}[/red]")

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
    
    # Initialize evaluator
    console.print("[bold blue]Initializing evaluator...")
    evaluator = AgentEvaluator(debug=True)
    console.print(f"[green]✓[/green] Evaluator initialized")
    
    # Format dataset for evaluation
    console.print("[bold blue]Formatting dataset for evaluation...")
    eval_dataset = evaluator.format_dataset_for_eval(examples)
    console.print(f"[green]✓[/green] Dataset formatted with {len(eval_dataset)} examples")
    
    # Import the agent to evaluate
    console.print("[bold blue]Importing agent for evaluation...")
    try:
        from customer_support_agent import create_customer_support_agent
        
        # Create agent for evaluation
        agent = create_customer_support_agent(
            model_id="google/gemini-1.5-pro",
            use_weave=True,
            temperature=0.2,
            planning_interval=1,
            max_steps=3
        )
        
        # Define a function that runs the agent and returns the result
        def run_agent(prompt):
            return agent.run(prompt)
        
        console.print(f"[green]✓[/green] Agent imported and ready for evaluation")
    except Exception as e:
        console.print(f"[red]Error importing agent: {str(e)}[/red]")
        return
    
    # Run evaluation
    with console.status("[bold blue]Running evaluation...", spinner="dots"):
        results = evaluator.run_evaluation(run_agent, eval_dataset)
    
    # Display results summary
    console.rule("[bold green]Evaluation Results")
    
    # Create a more detailed summary table
    table = Table(title="Summary Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Score", style="magenta")
    table.add_column("Rating", style="yellow")
    
    # Add rating interpretation
    def get_rating(score):
        if score >= 4.5: return "[bold green]Excellent[/bold green]"
        elif score >= 4.0: return "[green]Very Good[/green]"
        elif score >= 3.5: return "[blue]Good[/blue]"
        elif score >= 3.0: return "[yellow]Satisfactory[/yellow]"
        elif score >= 2.0: return "[orange]Needs Improvement[/orange]"
        else: return "[red]Poor[/red]"
    
    for metric, score in results["summary_metrics"].items():
        table.add_row(
            metric.replace("_", " ").title(), 
            f"{score:.2f}", 
            get_rating(score)
        )
    
    console.print(table)
    
    # Display path to results
    console.print(f"\n[bold green]Evaluation complete![/bold green]")
    console.print(f"[bold]Detailed results saved to:[/bold] [cyan]evaluation_results/[/cyan]")
    console.print(f"[bold]Visualizations saved to:[/bold] [cyan]evaluation_results/score_distribution.png[/cyan] and other PNG files")

if __name__ == "__main__":
    main()