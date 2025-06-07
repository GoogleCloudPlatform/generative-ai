import logging
from typing import Any, Dict, List

from models.llm_interface import LLMInterface
from tools.dataset_tools import DatasetTools

logger = logging.getLogger(__name__)


def create_resource_workflow(llm: LLMInterface, dataset_tools: DatasetTools):
    """Create a workflow for collecting resources for use cases.

    Args:
        llm: LLM interface for generating analysis.
        dataset_tools: Tools for finding datasets.

    Returns:
        A workflow function.
    """

    async def collect_resources(state: Dict[str, Any]) -> Dict[str, Any]:
        """Collect resources for use cases."""
        use_cases = state.get("use_cases", [])

        if not use_cases:
            return {"resources": {}}

        logger.info(f"Collecting resources for {len(use_cases)} use cases")

        # Initialize results
        resources = {}

        # Process each use case in sequence
        for use_case in use_cases:
            title = use_case.get("title", "")
            if not title:
                continue

            logger.info(f"Finding resources for use case: {title}")

            # Find datasets for the use case
            use_case_resources = await dataset_tools.find_datasets_for_use_case(
                use_case
            )

            # Store resources
            resources[title] = use_case_resources

            logger.info(
                f"Found {len(use_case_resources)} resources for use case: {title}"
            )

        return {"resources": resources}

    async def evaluate_resources(state: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate the relevance of resources for each use case."""
        use_cases = state.get("use_cases", [])
        resources = state.get("resources", {})

        if not use_cases or not resources:
            return {}

        evaluated_resources = {}

        for use_case in use_cases:
            title = use_case.get("title", "")
            if not title or title not in resources:
                continue

            use_case_resources = resources[title]
            if not use_case_resources:
                evaluated_resources[title] = []
                continue

            # Define JSON schema for relevance evaluation
            relevance_schema = {
                "type": "object",
                "properties": {
                    "resource_relevance": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "relevance_score": {
                                    "type": "number",
                                    "minimum": 1,
                                    "maximum": 10,
                                },
                                "relevance_notes": {"type": "string"},
                            },
                            "required": ["title", "relevance_score", "relevance_notes"],
                        },
                    }
                },
                "required": ["resource_relevance"],
            }

            # Prepare the prompt
            use_case_text = (
                f"USE CASE: {title}\n"
                + f"Description: {use_case.get('description', '')}\n"
                + f"Business Value: {use_case.get('business_value', '')}\n"
                + f"AI Technologies: {', '.join(use_case.get('ai_technologies', []))}\n"
                + f"Keywords: {', '.join(use_case.get('keywords', []))}"
            )

            resources_text = "\n\n".join(
                [
                    f"RESOURCE {i + 1}: {r.get('title', '')}\n"
                    + f"URL: {r.get('url', '')}\n"
                    + f"Source: {r.get('source', '')}\n"
                    + f"Description: {r.get('description', '')}\n"
                    + f"Found via query: {r.get('query', '')}"
                    for i, r in enumerate(
                        use_case_resources[:10]
                    )  # Limit to 10 resources for evaluation
                ]
            )

            prompt = f"""
Evaluate the relevance of the following resources for implementing this AI/GenAI use case:

{use_case_text}

RESOURCES:
{resources_text}

For each resource, provide:
1. A relevance score (1-10, with 10 being most relevant)
2. Brief notes explaining why the resource is relevant or not relevant
3. How the resource could be used for implementing the use case

Focus on both technical fit (does it contain the right kind of data/code?) and practical applicability.
"""

            system_prompt = """
You are a data science and AI resource specialist who evaluates the relevance and quality of datasets, code repositories, and other resources for AI implementation projects. You have expertise in identifying suitable resources for specific use cases.
"""

            try:
                # Generate relevance evaluation using the LLM
                result = await llm.generate_with_json_output(
                    prompt=prompt,
                    json_schema=relevance_schema,
                    system_prompt=system_prompt,
                    temperature=0.3,
                )

                relevance_items = result.get("resource_relevance", [])

                # Update resources with relevance scores
                title_to_resource = {r.get("title", ""): r for r in use_case_resources}

                for item in relevance_items:
                    resource_title = item.get("title", "")
                    if resource_title in title_to_resource:
                        title_to_resource[resource_title]["relevance_score"] = item.get(
                            "relevance_score", 5
                        )
                        title_to_resource[resource_title]["relevance_notes"] = item.get(
                            "relevance_notes", ""
                        )

                # Sort resources by relevance score
                evaluated_resources[title] = sorted(
                    use_case_resources,
                    key=lambda r: r.get("relevance_score", 0),
                    reverse=True,
                )

                # Limit to top 5 most relevant resources
                evaluated_resources[title] = evaluated_resources[title][:5]

            except Exception as e:
                logger.error(f"Error evaluating resource relevance: {e}")
                evaluated_resources[title] = use_case_resources

        return {"evaluated_resources": evaluated_resources}

    # Define the resource workflow
    async def resource_workflow(input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the resource workflow."""
        state = input_data.copy()

        # Step 1: Collect resources
        if "use_cases" in state and state["use_cases"]:
            resource_result = await collect_resources(state)
            state.update(resource_result)

        # Step 2: Evaluate resources
        if "resources" in state and state["resources"]:
            evaluation_result = await evaluate_resources(state)
            state.update(evaluation_result)

            # Update resources with evaluated resources if available
            if "evaluated_resources" in state:
                state["resources"] = state["evaluated_resources"]

        return state

    return resource_workflow
