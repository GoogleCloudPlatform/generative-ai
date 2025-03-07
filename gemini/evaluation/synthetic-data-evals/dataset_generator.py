# agent_evaluation/dataset_generator.py
import inspect
import json
import os
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Union

from config import WEAVE_PROJECT_NAME
from dotenv import load_dotenv
import instructor
from litellm import completion
import pandas as pd
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from smolagents import ActionStep, CodeAgent
import weave

os.environ["WEAVE_PRINT_CALL_LINK"] = "false"

# Create client instead of patching directly
client = instructor.from_litellm(completion)


class AgentStep(BaseModel):
    """Single step taken by agent"""

    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_output: Optional[Any] = None
    llm_response: str


class AgentTrajectory(BaseModel):
    """Complete sequence of agent actions"""

    steps: List[AgentStep]
    final_response: str


class EvaluationScores(BaseModel):
    """Scores and reasoning for an evaluation"""

    final_response: float
    steps: List[float]  # List of step scores
    trajectory: float
    reasoning: Dict[str, Union[str, List[str]]] = {  # Reasoning for each score
        "final_response": "",
        "steps": [],
        "trajectory": "",
    }


class EvaluationExample(BaseModel):
    """Single evaluation example with scores"""

    prompt: str
    tools_available: List[str]
    trajectory: AgentTrajectory
    scores: EvaluationScores
    metadata: Dict[str, Any]


class ScoreWithReasoning(BaseModel):
    """Score with explanation from judge"""

    score: float
    reasoning: str


class DatasetGenerator(weave.Model):
    # Define fields as class variables
    agent: CodeAgent
    judge_model: str = "gemini/gemini-1.5-pro"
    thresholds: Dict[str, float]
    debug: bool = False
    console: Optional[Console] = None

    DEFAULT_THRESHOLDS: ClassVar[Dict[str, float]] = {
        "final_response": 0.8,  # Threshold for accepting final response
        "single_step": 0.85,  # Threshold for each individual step
        "trajectory": 0.75,  # Threshold for overall trajectory
    }

    def model_post_init(self, __context: Any) -> None:
        """Initialize after Pydantic validation"""
        # Merge provided thresholds with defaults
        if self.thresholds is None:
            self.thresholds = self.DEFAULT_THRESHOLDS.copy()
        else:
            self.thresholds = {**self.DEFAULT_THRESHOLDS, **self.thresholds}

        self.console = Console()

        if self.debug:
            self.console.print("[bold blue]Initialized with thresholds:[/bold blue]")
            for key, value in self.thresholds.items():
                self.console.print(f"  {key}: {value}")

    @weave.op()
    def _run_agent(self, prompt: str) -> AgentTrajectory:
        """Execute agent and record steps"""
        if self.debug:
            self.console.rule("[bold blue]Running Agent")
            self.console.print(f"[yellow]Prompt:[/yellow] {prompt}\n")

        steps = []
        result = self.agent.run(prompt)

        # Convert function objects to their string representation
        if callable(result):
            result = inspect.getsource(result)
        elif not isinstance(result, str):
            result = str(result)

        for log in self.agent.memory.steps:
            if isinstance(log, ActionStep) and log.tool_calls:
                if self.debug:
                    self.console.print(
                        Panel(
                            f"[bold green]Step {len(steps) + 1}:[/bold green]\n"
                            f"Tool: {log.tool_calls[0].name}\n"
                            f"Args: {log.tool_calls[0].arguments}\n"
                            f"Output: {log.action_output}"
                        )
                    )

                try:
                    tool_args = (
                        {"code": log.tool_calls[0].arguments}
                        if isinstance(log.tool_calls[0].arguments, str)
                        else log.tool_calls[0].arguments
                    )

                    agent_step = AgentStep(
                        tool_name=log.tool_calls[0].name,
                        tool_args=tool_args,
                        tool_output=log.action_output,
                        llm_response=(
                            log.model_output_message.content
                            if log.model_output_message
                            else ""
                        ),
                    )
                    steps.append(agent_step)

                except Exception as e:
                    if self.debug:
                        self.console.print(f"[red]Error creating step: {str(e)}")
                    raise

        if self.debug:
            self.console.print(f"\n[green]Final Response:[/green] {result}\n")

        return AgentTrajectory(steps=steps, final_response=result)

    @weave.op()
    def _judge_final_response(
        self, prompt: str, response: str, tools_used: List[str]
    ) -> Tuple[float, str]:
        """Judge final response and return score with reasoning"""
        if self.debug:
            self.console.rule("[bold yellow]Judging Final Response")

        result = client.chat.completions.create(
            model=self.judge_model,
            response_model=ScoreWithReasoning,
            messages=[
                {
                    "role": "user",
                    "content": f"""Score this agent's response (0-1) and provide reasoning:
                User prompt: {prompt}
                Tools used: {tools_used}
                Final response: {response}
                
                Evaluate:
                1. Correctness and completeness
                2. Appropriate tool usage
                3. Clear communication
                
                Return a JSON with:
                {{"score": float between 0-1,
                  "reasoning": "Your detailed reasoning"}}""",
                }
            ],
        )

        if self.debug:
            self.console.print(
                f"[bold cyan]Final Response Score:[/bold cyan] {result.score:.2f}"
            )
            self.console.print(
                f"[bold cyan]Reasoning:[/bold cyan] {result.reasoning}\n"
            )

        return result.score, result.reasoning

    @weave.op()
    def _judge_step(self, prompt: str, step: AgentStep) -> Tuple[float, str]:
        """Judge single step and return score with reasoning"""
        if self.debug:
            self.console.rule("[yellow]Judging Step")
            tools_used = self._extract_tool_names_from_step(step)
            self.console.print(f"Tools Used: {tools_used}")

        # Extract actual tool usage from the LLM response
        tool_execution_info = ""
        if step.tool_name == "python_interpreter":
            # For python interpreter, show the code being executed
            code = step.tool_args.get("code", "") if step.tool_args else ""
            tool_execution_info = f"Code executed:\n{code}\n"
        else:
            # For direct tool calls, show the tool and its args
            tool_execution_info = (
                f"Tool: {step.tool_name}\nArguments: {step.tool_args}\n"
            )

        result = client.chat.completions.create(
            model=self.judge_model,
            response_model=ScoreWithReasoning,
            messages=[
                {
                    "role": "user",
                    "content": f"""Score this agent step (0-1) and provide reasoning:
                User prompt: {prompt}
                
                Execution:
                {tool_execution_info}
                Agent's reasoning: {step.llm_response}
                
                Evaluate:
                1. Quality of agent's reasoning and decision-making
                2. Appropriate use of tools or code
                3. Progress toward solving the original prompt
                4. Clarity and effectiveness of the step
                
                Return a JSON with:
                {{"score": float between 0-1,
                  "reasoning": "Your detailed reasoning"}}""",
                }
            ],
        )

        if self.debug:
            self.console.print(f"[bold cyan]Score:[/bold cyan] {result.score:.2f}")
            self.console.print(
                f"[bold cyan]Reasoning:[/bold cyan] {result.reasoning}\n"
            )

        return result.score, result.reasoning

    @weave.op()
    def _judge_trajectory(
        self, prompt: str, steps: List[AgentStep]
    ) -> Tuple[float, str]:
        """Judge full trajectory and return score with reasoning"""
        if self.debug:
            self.console.rule("[yellow]Judging Trajectory")
            for i, step in enumerate(steps, 1):
                tools = self._extract_tool_names_from_step(step)
                if tools:
                    self.console.print(f"Step {i} Tools: {tools}")

        # Format steps for prompt
        steps_text = "\n\n".join(
            [
                f"Step {i+1}:\n"
                f"Tool: {step.tool_name}\n"
                f"Input: {step.tool_args}\n"
                f"Output: {step.tool_output}\n"
                f"Agent response: {step.llm_response}"
                for i, step in enumerate(steps)
            ]
        )

        result = client.chat.completions.create(
            model=self.judge_model,
            response_model=ScoreWithReasoning,
            messages=[
                {
                    "role": "user",
                    "content": f"""Score this agent's reasoning trajectory (0-1) and provide reasoning:
                User prompt: {prompt}
                
                {steps_text}
                
                Evaluate:
                1. Logical progression of steps
                2. Efficient path to solution
                3. Appropriate tool usage
                4. Learning from observations
                
                Return a JSON with:
                {{"score": float between 0-1,
                  "reasoning": "Your detailed reasoning"}}""",
                }
            ],
        )

        if self.debug:
            self.console.print(
                f"[bold cyan]Trajectory Score:[/bold cyan] {result.score:.2f}"
            )
            self.console.print(
                f"[bold cyan]Reasoning:[/bold cyan] {result.reasoning}\n"
            )

        return result.score, result.reasoning

    @weave.op()
    def _extract_tool_names_from_step(self, step: AgentStep) -> List[str]:
        """Extract actual tool names from a step, handling CodeAgent's python_interpreter case"""
        if step.tool_name == "python_interpreter":
            code = step.tool_args.get("code", "")
            tools_found = []
            for tool_name in self.agent.tools.keys():
                if tool_name in code and tool_name != "python_interpreter":
                    tools_found.append(tool_name)

            if self.debug:
                # Only show debug if we found tools or if it's not just a code execution
                if tools_found or any(
                    tool in code for tool in ["def ", "class ", "import "]
                ):
                    self.console.print(
                        Panel(
                            f"[bold blue]Code Analysis[/bold blue]\n"
                            f"[yellow]Code:[/yellow]\n{code}\n"
                            f"[green]Tools Found:[/green] {tools_found or 'No tools, just code execution'}"
                        )
                    )
            return tools_found
        else:
            return [step.tool_name] if step.tool_name else []

    @weave.op()
    def _generate_metadata(self, trajectory: AgentTrajectory) -> Dict[str, Any]:
        """Generate metadata like number of steps, tools used, etc"""
        tools_used = []
        for step in trajectory.steps:
            tools_used.extend(self._extract_tool_names_from_step(step))

        if self.debug:
            self.console.print(
                Panel(
                    "[bold blue]Run Summary[/bold blue]\n"
                    f"Steps: {len(trajectory.steps)}\n"
                    f"Tools Used: {list(set(tools_used))}\n"
                    f"Planning: {'Enabled' if self.agent.planning_interval > 0 else 'Disabled'}"
                )
            )

        return {
            "num_steps": len(trajectory.steps),
            "tools_used": list(set(tools_used)),  # Remove duplicates
            "has_planning": self.agent.planning_interval > 0,
        }

    @weave.op()
    def save_dataset(
        self,
        examples: List[EvaluationExample],
        output_path: str = "agent_evaluation_dataset.json",
        save_to_weave: bool = True,
    ) -> str:
        """Export evaluation examples to a format compatible with the evaluator"""
        if not examples:
            raise ValueError("No examples to export")

        formatted_examples = []

        for example in examples:
            # Extract tool usage from trajectory
            tools_used = []
            for step in example.trajectory.steps:
                step_tools = []
                if step.tool_name == "python_interpreter":
                    # For python interpreter, extract tools from code
                    if step.tool_args and "code" in step.tool_args:
                        code = step.tool_args["code"]
                        for tool in example.tools_available:
                            if tool in code and tool != "python_interpreter":
                                step_tools.append(tool)
                elif step.tool_name:
                    step_tools.append(step.tool_name)

                tools_used.extend(step_tools)

            # Remove duplicates while preserving order
            unique_tools = []
            for tool in tools_used:
                if tool not in unique_tools:
                    unique_tools.append(tool)

            # Format expected trajectory
            expected_trajectory = []
            for i, step in enumerate(example.trajectory.steps):
                step_data = {
                    "step_number": i + 1,
                    "tool_name": step.tool_name,
                    "tool_input": step.tool_args,
                    "tool_output": step.tool_output,
                    "reasoning": step.llm_response,
                }
                expected_trajectory.append(step_data)

            # Create validation criteria based on scores and reasoning
            validation_criteria = {
                "final_response": {
                    "min_score": example.scores.final_response,
                    "criteria": example.scores.reasoning["final_response"],
                },
                "tool_selection": {
                    "expected_tools": unique_tools,
                    "criteria": "Tools should be called in appropriate order with correct arguments",
                },
                "reasoning_quality": {
                    "criteria": example.scores.reasoning["trajectory"]
                },
            }

            # Determine difficulty based on number of steps and tools
            difficulty = "easy" if len(example.trajectory.steps) <= 2 else "medium"
            if len(example.trajectory.steps) > 4:
                difficulty = "hard"

            # Create tags based on metadata and tools
            tags = ["agent_evaluation"]
            if example.metadata.get("has_planning", False):
                tags.append("planning_enabled")

            # Add tool-specific tags
            for tool in unique_tools:
                tags.append(f"uses_{tool}")

            formatted_example = {
                "input": example.prompt,
                "expected_final_response": example.trajectory.final_response,
                "tools_available": example.tools_available,
                "expected_trajectory": expected_trajectory,
                "validation_criteria": validation_criteria,
                "difficulty": difficulty,
                "tags": tags,
                "metadata": example.metadata,
            }

            formatted_examples.append(formatted_example)

        # Write to JSON file
        with open(output_path, "w") as f:
            json.dump(formatted_examples, f, indent=2)

        result_message = f"Exported {len(formatted_examples)} examples to {output_path}"

        # Publish to Weave if requested
        if save_to_weave and formatted_examples:
            # Create a Weave dataset with the formatted examples
            dataset_name = os.path.splitext(os.path.basename(output_path))[0]

            # Convert the formatted examples to the format expected by Weave Dataset
            weave_rows = []
            for example in formatted_examples:
                weave_rows.append(
                    {
                        "prompt": example["input"],
                        "expected_response": example["expected_final_response"],
                        "tools_available": example["tools_available"],
                        "expected_trajectory": example["expected_trajectory"],
                        "validation_criteria": example["validation_criteria"],
                        "difficulty": example["difficulty"],
                        "tags": example["tags"],
                        "metadata": example["metadata"],
                    }
                )

            # Create and publish the dataset
            dataset = weave.Dataset(name=dataset_name, rows=weave_rows)
            ref = weave.publish(dataset)

            result_message += (
                f" and published to Weave as '{dataset_name}' (ref: {ref.uri()})"
            )

            if self.debug:
                self.console.print(
                    f"[bold green]Dataset published to Weave:[/bold green] {ref.uri()}"
                )

        return result_message

    @weave.op()
    def generate_dataset(self, input_prompts: List[str]) -> List[EvaluationExample]:
        """Generate evaluation dataset from prompts"""
        examples = []

        for i, prompt in enumerate(input_prompts, 1):
            if self.debug:
                self.console.rule(
                    f"[bold red]Processing Prompt {i}/{len(input_prompts)}"
                )

            trajectory = self._run_agent(prompt)

            if self.debug:
                self.console.print("[bold]Collecting Scores...[/bold]")

            # Get list of actual tool names that were used
            tools_used = []
            for step in trajectory.steps:
                tools_used.extend(self._extract_tool_names_from_step(step))
            tools_used = list(set(tools_used))  # Remove duplicates

            # Get scores with reasoning
            final_response_score, final_response_reasoning = self._judge_final_response(
                prompt, trajectory.final_response, tools_used
            )

            step_scores_with_reasoning = [
                self._judge_step(prompt, step) for step in trajectory.steps
            ]

            trajectory_score, trajectory_reasoning = self._judge_trajectory(
                prompt, trajectory.steps
            )

            # Apply thresholds
            if final_response_score < self.thresholds["final_response"]:
                if self.debug:
                    self.console.print(
                        f"[red]Final response score {final_response_score:.2f} below threshold {self.thresholds['final_response']}"
                    )
                continue

            if any(
                score < self.thresholds["single_step"]
                for score, _ in step_scores_with_reasoning
            ):
                if self.debug:
                    self.console.print(
                        f"[red]Some step scores below threshold {self.thresholds['single_step']}"
                    )
                continue

            if trajectory_score < self.thresholds["trajectory"]:
                if self.debug:
                    self.console.print(
                        f"[red]Trajectory score {trajectory_score:.2f} below threshold {self.thresholds['trajectory']}"
                    )
                continue

            scores = EvaluationScores(
                final_response=final_response_score,
                steps=[score for score, _ in step_scores_with_reasoning],
                trajectory=trajectory_score,
                reasoning={
                    "final_response": final_response_reasoning,
                    "steps": [reasoning for _, reasoning in step_scores_with_reasoning],
                    "trajectory": trajectory_reasoning,
                },
            )

            if self.debug:
                table = Table(title="Evaluation Scores")
                table.add_column("Metric", style="cyan")
                table.add_column("Score", style="magenta")
                table.add_column("Reasoning", style="yellow")

                table.add_row(
                    "Final Response",
                    f"{scores.final_response:.2f}",
                    scores.reasoning["final_response"],
                )
                table.add_row(
                    "Trajectory",
                    f"{scores.trajectory:.2f}",
                    scores.reasoning["trajectory"],
                )
                table.add_row(
                    "Step Scores",
                    ", ".join(f"{s:.2f}" for s in scores.steps),
                    "\n".join(scores.reasoning["steps"]),
                )
                self.console.print(table)

            # Get available tools from agent's tools dictionary
            available_tools = list(self.agent.tools.keys())

            # Generate metadata
            metadata = {
                "model": self.agent.model.__class__.__name__,
                "model_id": getattr(self.agent.model, "model_id", None),
                **self._generate_metadata(trajectory),  # Add the additional metadata
            }

            examples.append(
                EvaluationExample(
                    prompt=prompt,
                    tools_available=available_tools,
                    trajectory=trajectory,
                    scores=scores,
                    metadata=metadata,
                )
            )

        return examples


@weave.op()
def generate_ecommerce_prompts(debug: bool = False, num_prompts: int = 10) -> List[str]:
    """Generate realistic e-commerce customer support prompts based on available tools and data"""
    console = Console() if debug else None

    if debug and console:
        console.rule("[bold blue]Generating E-commerce Prompts")

    # Load product and order data to generate realistic prompts
    try:
        products_df = pd.read_csv("data/products.csv")
        orders_df = pd.read_csv("data/orders.csv")

        # Sample real product IDs, categories, and customer IDs
        product_ids = (
            products_df["product_id"].sample(min(10, len(products_df))).tolist()
        )
        categories = (
            products_df["category"]
            .drop_duplicates()
            .sample(min(10, products_df["category"].nunique()))
            .tolist()
        )
        customer_ids = (
            orders_df["customer_id"]
            .drop_duplicates()
            .sample(min(10, orders_df["customer_id"].nunique()))
            .tolist()
        )
        order_ids = orders_df["order_id"].sample(min(10, len(orders_df))).tolist()

        if debug and console:
            console.print(
                f"Loaded {len(products_df)} products and {len(orders_df)} orders"
            )
            console.print(f"Sample product IDs: {product_ids[:3]}")
            console.print(f"Sample categories: {categories[:3]}")
    except Exception as e:
        if debug and console:
            console.print(f"[red]Error loading product/order data: {str(e)}")
            console.print("[yellow]Falling back to simple prompts")

        # Fallback to simple prompts if data loading fails
        return [
            "What products do you sell?",
            "How can I check my order status?",
            "Tell me about your return policy",
            "Do you have any electronics?",
            "How do I contact customer support?",
            "What payment methods do you accept?",
            "Do you ship internationally?",
            "How long does shipping take?",
            "Can I cancel my order?",
            "Do you offer gift wrapping?",
        ][:num_prompts]

    # Create specific prompts that test different agent capabilities
    prompts = [
        # 1. Basic product search by category
        f"I'm looking for products in the {categories[0]} category. What do you have?",
        # 2. Order status check
        f"Can you check the status of my order {order_ids[0]}?",
        # 3. Price check for specific product
        f"How much does product {product_ids[0]} cost?",
        # 4. Customer order history lookup
        f"Can you show me my recent orders? My customer ID is {customer_ids[0]}",
        # 5. Complex query combining product search and order status
        f"I'm looking for {categories[1]} products and also want to check my order {order_ids[1]}",
        # 6. Product recommendation request
        f"What's your best {categories[2]} product? I need something reliable.",
        # 7. Order tracking with specific concerns
        f"I placed an order with ID {order_ids[2]} three days ago and haven't received any updates. Can you help?",
        # 8. Product comparison within category
        f"I want to compare the top products in the {categories[3]} category. What options do you have?",
        # 9. Customer with specific product requirements
        f"I need a {categories[4]} product that costs less than $50. What do you recommend?",
        # 10. Complex multi-tool query with order history and new purchase
        f"I'm customer {customer_ids[1]} and I previously bought a {categories[5]} product. I'd like something similar but better. Also, when will my order {order_ids[3]} arrive?",
    ]

    # Limit to the requested number of prompts
    prompts = prompts[:num_prompts]

    if debug:
        console.print(f"[green]Generated {len(prompts)} e-commerce prompts")
        for i, prompt in enumerate(prompts, 1):
            console.print(f"[cyan]Sample {i}:[/cyan] {prompt}")

    return prompts


@weave.op()
def create_customer_support_agent_evaluation_dataset(
    generator: DatasetGenerator, agent: CodeAgent, num_prompts: int = 10
) -> List[EvaluationExample]:
    """Create a customer support agent evaluation dataset with realistic e-commerce prompts"""
    if generator.debug:
        generator.console.rule(
            "[bold red]Creating Customer Support Agent Evaluation Dataset"
        )
        generator.console.print(f"Agent model: {agent.model.__class__.__name__}")
        generator.console.print(f"Available tools: {list(agent.tools.keys())}")

    # Generate realistic e-commerce prompts
    prompts = generate_ecommerce_prompts(debug=generator.debug, num_prompts=num_prompts)

    # Run evaluation on the prompts
    return generator.generate_dataset(prompts)


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    weave.init(WEAVE_PROJECT_NAME)

    # Create a rich console for pretty output
    console = Console()
    console.rule("[bold magenta]Customer Support Agent Evaluation")

    # Import the customer support agent
    from customer_support_agent import create_customer_support_agent

    console.print("[bold blue]Creating Customer Support Agent...[/bold blue]")

    # Create a customer support agent for evaluation
    agent = create_customer_support_agent(
        model_id="google/gemini-1.5-pro",
        use_weave=True,
        temperature=0.2,  # Lower temperature for more consistent responses
        planning_interval=1,  # Plan every step
        max_steps=3,  # Allow up to 3 steps for complex queries
    )

    console.print("[bold green]✓[/bold green] Agent created successfully")
    console.print(
        "[dim]Model: google/gemini-1.5-pro | Planning: Enabled | Max Steps: 3[/dim]"
    )

    # Initialize dataset generator with debug mode
    console.rule("[bold blue]Initializing Dataset Generator")
    generator = DatasetGenerator(
        agent=agent,
        judge_model="gemini/gemini-1.5-pro",
        thresholds={"final_response": 0.7, "single_step": 0.7, "trajectory": 0.7},
        debug=True,  # Enable debug output
    )
    console.print(
        "[bold green]✓[/bold green] Generator initialized with thresholds: [dim]final_response=0.7, single_step=0.7, trajectory=0.7[/dim]"
    )

    # Generate evaluation dataset
    console.rule("[bold blue]Generating Evaluation Dataset")
    examples = create_customer_support_agent_evaluation_dataset(
        generator, agent, num_prompts=2
    )

    # Print results in a nice format
    console.rule("[bold green]Results Summary")
    console.print(f"[bold]Generated {len(examples)} evaluation examples[/bold]")

    for i, example in enumerate(examples, 1):
        panel = Panel(
            f"[bold cyan]Prompt:[/bold cyan] {example.prompt}\n\n"
            f"[bold yellow]Metrics:[/bold yellow]\n"
            f"  • Final response score: [magenta]{example.scores.final_response:.2f}[/magenta]\n"
            f"  • Step scores: [magenta]{', '.join([f'{s:.2f}' for s in example.scores.steps])}[/magenta]\n"
            f"  • Trajectory score: [magenta]{example.scores.trajectory:.2f}[/magenta]\n\n"
            f"[bold yellow]Details:[/bold yellow]\n"
            f"  • Tools available: [dim]{', '.join(example.tools_available)}[/dim]\n"
            f"  • Tools used: [dim]{', '.join(example.metadata['tools_used'])}[/dim]\n"
            f"  • Steps taken: [dim]{example.metadata['num_steps']}[/dim]\n"
            f"  • Planning: [dim]{'Enabled' if example.metadata['has_planning'] else 'Disabled'}[/dim]",
            title=f"[bold]Example {i}/{len(examples)}[/bold]",
            border_style="blue",
        )
        console.print(panel)

    console.rule("[bold green]Evaluation Complete")

    # Export the dataset for evaluation - now using the class method
    export_path = "synthetic_agent_dataset.json"
    export_result = generator.save_dataset(examples, export_path)
    console.print(f"[bold green]{export_result}")
