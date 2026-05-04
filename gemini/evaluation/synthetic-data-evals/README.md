# Agent Evaluation Framework

This repository contains a framework for generating, evaluating, and analyzing the performance of LLM-powered agents in customer support scenarios.

## Overview

The framework consists of three main components:

1. **Customer Support Agent** - An LLM-powered agent with tools for handling e-commerce customer queries
2. **Dataset Generator** - A system for creating synthetic evaluation datasets with realistic customer queries
3. **Agent Evaluator** - A comprehensive evaluation system for measuring agent performance

## Customer Support Agent

The customer support agent is built using the `smolagents` framework and provides several tools for handling e-commerce queries:

- `ProductSearchTool` - Search product catalog by name, category, or description
- `OrderStatusTool` - Check order status by order ID
- `CategoryBrowseTool` - Browse products by category
- `PriceCheckTool` - Check product price by product ID
- `CustomerOrderHistoryTool` - Get order history for a customer

The agent can be configured with different LLM models, including Gemini 1.5 Pro, and supports planning capabilities to handle complex multistep queries.

```python
agent = create_customer_support_agent(
    model_id="google/gemini-1.5-pro",
    use_weave=True,
    temperature=0.2,
    planning_interval=1,
    max_steps=3
)
```

## Dataset Generator

The dataset generator creates realistic evaluation examples by:

1. Generating diverse e-commerce customer queries
2. Running the agent on these queries and recording its trajectory
3. Evaluating each step and the final response using a judge model
4. Filtering examples based on quality thresholds
5. Saving high-quality examples to a dataset for evaluation

```python
generator = DatasetGenerator(
    agent=agent,
    judge_model="gemini/gemini-1.5-pro",
    thresholds={
        "final_response": 0.7,
        "single_step": 0.7,
        "trajectory": 0.7
    },
    debug=True
)

examples = create_customer_support_agent_evaluation_dataset(generator, agent, num_prompts=10)
```

## Agent Evaluator

The evaluator provides comprehensive metrics for agent performance:

- **Response Correctness** - Accuracy and completeness of the agent's final response
- **Tool Selection** - Appropriate use of available tools
- **Trajectory Analysis** - Efficiency and effectiveness of the agent's path to solution
- **Reasoning Quality** - Quality of the agent's reasoning process
- **Coherence** - Consistency and clarity of the agent's communication

The evaluator generates detailed reports, visualizations, and metrics to analyze agent performance.

```python
evaluator = AgentEvaluator(
    model_name="gemini-1.5-pro",
    temperature=0.1,
    verbosity=2,
    use_weave=True
)

results = evaluator.run_evaluation(agent, eval_dataset)
```

## Getting Started

1. Install dependencies:
   ```
   uv sync
   ```

2. Set up environment variables (some of these will autopopulate if you run `setup.py`):
   ```
   # Create a .env file with your API keys or colab secrets
    GEMINI_API_KEY
    HUGGING_FACE_HUB_TOKEN
    VERTEX_PROJECT_ID
    VERTEX_LOCATION
    VERTEX_MODEL_ID
    VERTEX_ENDPOINT_ID
    DEEPSEEK_ENDPOINT_ID
   ```

3. Generate evaluation dataset:
   ```python
   from dataset_generator import DatasetGenerator, create_customer_support_agent_evaluation_dataset
   from customer_support_agent import create_customer_support_agent
   
   agent = create_customer_support_agent()
   generator = DatasetGenerator(agent=agent)
   examples = create_customer_support_agent_evaluation_dataset(generator, agent)
   generator.save_dataset(examples, "evaluation_dataset.json")
   ```

4. Run evaluation:
   ```python
   from evaluator import AgentEvaluator, load_dataset
   
   eval_dataset = load_dataset("evaluation_dataset.json")
   evaluator = AgentEvaluator()
   results = evaluator.run_evaluation(agent, eval_dataset)
   ```

## Features

- **Realistic Data Generation**: Creates synthetic but realistic customer queries based on e-commerce data
- **Comprehensive Evaluation**: Measures multiple aspects of agent performance
- **Visualization**: Generates plots and tables for analysis
- **Weave Integration**: Tracks experiments and results with Weave
  - Logs agent trajectories and evaluation metrics
  - Enables experiment comparison across different agent configurations
  - Provides interactive dashboards for analyzing agent performance
  - Supports versioning of evaluation datasets and results
  - Facilitates collaboration through shareable experiment links
- **Configurable Thresholds**: Adjustable quality thresholds for dataset generation

## Weave Integration

The framework leverages Weave for experiment tracking and visualization:

1. **Experiment Tracking**: Each agent run is logged as a Weave experiment with detailed metrics
2. **Trajectory Visualization**: Agent trajectories are visualized step-by-step for analysis
3. **Comparative Analysis**: Compare performance across different agent configurations and models
4. **Custom Dashboards**: Create custom dashboards to monitor specific metrics
5. **Artifact Management**: Store and version datasets, agent configurations, and evaluation results

```python
# Enable Weave logging in agent creation
agent = create_customer_support_agent(
    model_id="google/gemini-1.5-pro",
    use_weave=True,  # Enable Weave logging
    temperature=0.2
)

# Enable Weave in evaluator
evaluator = AgentEvaluator(
    model_name="gemini-1.5-pro",
    use_weave=True,  # Enable Weave logging
    verbosity=2
)
```

## Requirements

- Python 3.8+
- Vertex AI API access
- [Weights & Biases account](https://wandb.ai)
- Required Python packages (see pyproject.toml)

## Contributors

- [Anish Shah](https://github.com/ash0ts)