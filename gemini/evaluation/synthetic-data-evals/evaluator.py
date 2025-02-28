from typing import Dict, List, Any
import pandas as pd
from vertexai.generative_models import GenerativeModel, GenerationConfig
from vertexai.evaluation import (
    EvalTask, 
    PointwiseMetric,
    PointwiseMetricPromptTemplate,
    constants
)
from dataclasses import asdict
import json

class AgentEvaluator:
    def __init__(
        self,
        model_name: str = "gemini-1.5-pro",
        temperature: float = 0.1
    ):
        self.generation_config = GenerationConfig(
            temperature=temperature,
        )
        self.model = GenerativeModel(
            model_name=model_name,
            generation_config=self.generation_config
        )

    def format_dataset_for_eval(self, examples: List[Dict]) -> pd.DataFrame:
        """Convert our dataset format to Vertex AI Eval format"""
        eval_data = []
        
        for example in examples:
            eval_row = {
                "context": example["input"],
                "reference": example["expected_final_response"],
                "tools_available": json.dumps(example["tools_available"]),
                "expected_trajectory": json.dumps(example["expected_trajectory"]),
                "validation_criteria": json.dumps(example["validation_criteria"]),
                "difficulty": example["difficulty"],
                "tags": json.dumps(example["tags"])
            }
            eval_data.append(eval_row)
            
        return pd.DataFrame(eval_data)

    def define_agent_metrics(self) -> List[PointwiseMetric]:
        """Define custom metrics for agent evaluation"""
        
        # Tool Selection Accuracy Metric
        tool_selection_criteria = {
            "Correct Tool": "Selected the appropriate tool for the task",
            "Valid Arguments": "Provided correct arguments to the tool",
            "Sequence": "Tools called in logical order"
        }
        
        tool_selection_rubric = {
            "5": "Perfect tool selection with correct arguments and sequence",
            "4": "Correct tools but minor issues with arguments or sequence",
            "3": "Some incorrect tool selections or argument issues",
            "2": "Major issues with tool selection or arguments",
            "1": "Completely incorrect tool usage"
        }
        
        tool_selection_metric = PointwiseMetric(
            metric="tool_selection_accuracy",
            metric_prompt_template=PointwiseMetricPromptTemplate(
                criteria=tool_selection_criteria,
                rating_rubric=tool_selection_rubric
            )
        )

        # Memory Usage Metric
        memory_prompt = """
        Evaluate how effectively the agent uses its memory and context:
        
        Context: {context}
        Expected Memory Usage: {reference}
        Actual Memory Usage: {candidate}
        
        Score from 1-5 where:
        5: Perfect memory usage and context integration
        4: Good memory usage with minor inconsistencies
        3: Adequate memory usage but some context lost
        2: Poor memory usage with significant context loss
        1: Failed to maintain necessary context
        
        Provide score and explanation.
        """
        
        memory_metric = PointwiseMetric(
            metric="memory_effectiveness",
            metric_prompt_template=memory_prompt
        )

        # Planning Quality Metric
        planning_prompt = """
        Evaluate the agent's planning quality:
        
        Task: {context}
        Expected Plan: {reference}
        Actual Plan: {candidate}
        
        Score from 1-5 where:
        5: Optimal planning with clear reasoning
        4: Good planning with minor inefficiencies
        3: Adequate planning but could be improved
        2: Poor planning with major inefficiencies
        1: No clear planning or completely ineffective
        
        Provide score and explanation.
        """
        
        planning_metric = PointwiseMetric(
            metric="planning_quality",
            metric_prompt_template=planning_prompt
        )

        # Combine with built-in metrics
        metrics = [
            tool_selection_metric,
            memory_metric, 
            planning_metric,
            constants.Metric.GROUNDEDNESS,
            constants.Metric.COHERENCE,
            constants.Metric.FLUENCY
        ]
        
        return metrics

    def run_evaluation(self, eval_dataset: pd.DataFrame) -> Dict:
        """Run full evaluation using Vertex AI"""
        
        metrics = self.define_agent_metrics()
        
        eval_task = EvalTask(
            dataset=eval_dataset,
            metrics=metrics,
            experiment="agent_evaluation"
        )
        
        eval_result = eval_task.evaluate(
            model=self.model,
            experiment_run_name="agent_eval_run"
        )
        
        return {
            "summary_metrics": eval_result.summary_metrics,
            "detailed_metrics": eval_result.metrics_table
        }

def main():
    # Load generated dataset
    with open("synthetic_agent_dataset.json", "r") as f:
        examples = json.load(f)
    
    # Initialize evaluator
    evaluator = AgentEvaluator()
    
    # Format dataset for evaluation
    eval_dataset = evaluator.format_dataset_for_eval(examples)
    
    # Run evaluation
    results = evaluator.run_evaluation(eval_dataset)
    
    # Save results
    with open("evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("Evaluation complete! Results saved to evaluation_results.json")

if __name__ == "__main__":
    main()