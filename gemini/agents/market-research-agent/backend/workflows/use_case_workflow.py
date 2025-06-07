import logging
from typing import Any, Dict

from models.llm_interface import LLMInterface
from tools.analysis_tools import AnalysisTools

logger = logging.getLogger(__name__)


def create_use_case_workflow(llm: LLMInterface, analysis_tools: AnalysisTools):
    """Create a workflow for generating AI use cases.

    Args:
        llm: LLM interface for generating analysis.
        analysis_tools: Tools for analyzing information.

    Returns:
        A workflow function.
    """

    async def generate_use_cases(state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI use cases based on company and industry information."""
        company_info = state.get("company_info", {})
        industry_info = state.get("industry_info", {})
        num_use_cases = state.get("num_use_cases", 5)

        try:
            logger.info(
                f"Generating use cases for {company_info.get('name', 'company')}"
            )
            use_cases = await analysis_tools.extract_use_cases(
                company_info=company_info,
                industry_info=industry_info,
                num_use_cases=num_use_cases,
            )
            return {"use_cases": use_cases}
        except Exception as e:
            logger.error(f"Error generating use cases: {e}")
            return {"use_cases": [], "error": str(e)}

    async def prioritize_use_cases(state: Dict[str, Any]) -> Dict[str, Any]:
        """Prioritize use cases based on company needs."""
        company_info = state.get("company_info", {})
        use_cases = state.get("use_cases", [])

        if not use_cases:
            return {"prioritized_use_cases": []}

        try:
            logger.info(f"Prioritizing {len(use_cases)} use cases")
            prioritized_use_cases = await analysis_tools.prioritize_use_cases(
                use_cases=use_cases, company_info=company_info
            )
            return {"prioritized_use_cases": prioritized_use_cases}
        except Exception as e:
            logger.error(f"Error prioritizing use cases: {e}")
            return {"prioritized_use_cases": use_cases, "error": str(e)}

    async def add_keywords(state: Dict[str, Any]) -> Dict[str, Any]:
        """Add keywords to use cases for resource retrieval."""
        use_cases = state.get("prioritized_use_cases", [])

        if not use_cases:
            return {}

        # Define JSON schema for keywords
        keywords_schema = {
            "type": "object",
            "properties": {
                "use_case_keywords": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "use_case_title": {"type": "string"},
                            "keywords": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["use_case_title", "keywords"],
                    },
                }
            },
            "required": ["use_case_keywords"],
        }

        # Prepare the prompt
        use_cases_text = "\n\n".join(
            [
                f"USE CASE: {uc.get('title', '')}\n"
                + f"Description: {uc.get('description', '')}\n"
                + f"Business Value: {uc.get('business_value', '')}\n"
                + f"Implementation Complexity: {uc.get('implementation_complexity', 'Unknown')}\n"
                + f"AI Technologies: {', '.join(uc.get('ai_technologies', []))}"
                for uc in use_cases
            ]
        )

        prompt = f"""
For each of the following AI and GenAI use cases, provide a list of 5-7 relevant keywords that would be useful for finding datasets, implementation resources, and research papers.

USE CASES:
{use_cases_text}

For each use case, include specific technical terms, industry-specific terminology, and relevant AI model types that would yield good search results.
"""

        system_prompt = """
You are a technical research specialist who identifies precise, relevant keywords for AI and ML research and resource discovery. You have deep knowledge of AI terminology, datasets, and implementation resources.
"""

        try:
            # Generate keywords using the LLM
            result = await llm.generate_with_json_output(
                prompt=prompt,
                json_schema=keywords_schema,
                system_prompt=system_prompt,
                temperature=0.4,
            )

            # Add keywords to use cases
            keyword_map = {
                item["use_case_title"]: item["keywords"]
                for item in result.get("use_case_keywords", [])
            }

            use_cases_with_keywords = []
            for uc in use_cases:
                uc_with_keywords = uc.copy()
                title = uc.get("title", "")
                if title in keyword_map:
                    uc_with_keywords["keywords"] = keyword_map[title]
                else:
                    # If no keywords found, extract from AI technologies
                    uc_with_keywords["keywords"] = uc.get("ai_technologies", [])
                use_cases_with_keywords.append(uc_with_keywords)

            return {"use_cases_with_keywords": use_cases_with_keywords}

        except Exception as e:
            logger.error(f"Error adding keywords to use cases: {e}")
            # Ensure all use cases have at least some keywords
            use_cases_with_keywords = []
            for uc in use_cases:
                uc_with_keywords = uc.copy()
                if "keywords" not in uc_with_keywords:
                    uc_with_keywords["keywords"] = uc.get("ai_technologies", [])
                use_cases_with_keywords.append(uc_with_keywords)

            return {"use_cases_with_keywords": use_cases_with_keywords, "error": str(e)}

    # Define the use case workflow
    async def use_case_workflow(input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the use case workflow."""
        state = input_data.copy()

        # Step 1: Generate use cases
        use_case_result = await generate_use_cases(state)
        state.update(use_case_result)

        # Step 2: Prioritize use cases
        if "use_cases" in state and state["use_cases"]:
            prioritize_result = await prioritize_use_cases(state)
            state.update(prioritize_result)

        # Step 3: Add keywords to use cases
        if "prioritized_use_cases" in state and state["prioritized_use_cases"]:
            keyword_result = await add_keywords(state)
            state.update(keyword_result)

            # Make sure the main use_cases field is updated with the latest version
            if "use_cases_with_keywords" in state:
                state["use_cases"] = state["use_cases_with_keywords"]

        return state

    return use_case_workflow
