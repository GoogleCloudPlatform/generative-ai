import logging
from typing import Any, Dict, List, Optional

from models.llm_interface import LLMInterface
from tools.dataset_tools import DatasetTools

logger = logging.getLogger(__name__)


class ResourceCollectionAgent:
    """Agent for collecting implementation resources for AI use cases."""

    def __init__(self, llm: LLMInterface, dataset_tools: DatasetTools):
        """Initialize the resource collection agent.

        Args:
            llm: Language model interface.
            dataset_tools: Tools for collecting datasets and resources.
        """
        self.llm = llm
        self.dataset_tools = dataset_tools

    async def collect_resources(
        self, use_cases: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Collect implementation resources for an AI use case.

        Args:
            use_case: The AI use case to collect resources for.

        Returns:
            Dictionary mapping use case titles to lists of resources.
        """
        if not use_cases:
            return {}

        logger.info(f"Collecting resources for {len(use_cases)} use cases")

        # Initialize results
        resources = {}

        # Process each use case in sequence
        for use_case in use_cases:
            title = use_case.get("title", "")
            if not title:
                continue

            logger.info(f"Collecting resources for use case: {title}")

            # Find datasets for the use case
            use_case_resources = await self.dataset_tools.find_datasets_for_use_case(
                use_case
            )

            # Store resources
            resources[title] = use_case_resources

            logger.info(
                f"Found {len(use_case_resources)} resources for use case: {title}"
            )

        # Evaluate resource relevance
        await self._evaluate_resource_relevance(resources, use_cases)

        return resources

    async def _evaluate_resource_relevance(
        self,
        resources: Dict[str, List[Dict[str, Any]]],
        use_cases: List[Dict[str, Any]],
    ) -> None:
        """Evaluate the relevance of resources for each use case.

        Args:
            resources: Dictionary mapping use case titles to lists of resources.
            use_cases: List of use case dictionaries.
        """
        for use_case in use_cases:
            title = use_case.get("title", "")
            if not title or title not in resources:
                continue

            use_case_resources = resources[title]
            if not use_case_resources:
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
            Evaluate the relevance of the following resources for implementing this AI/Gen AI use case:

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
                result = await self.llm.generate_with_json_output(
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
                resources[title] = sorted(
                    use_case_resources,
                    key=lambda r: r.get("relevance_score", 0),
                    reverse=True,
                )

                # Limit to top 5 most relevant resources
                resources[title] = resources[title][:5]

            except Exception as e:
                logger.error(f"Error evaluating resource relevance: {e}")
