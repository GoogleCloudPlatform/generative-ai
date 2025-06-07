import logging
from typing import Any, Dict, List, Optional

from models.llm_interface import LLMInterface
from tools.analysis_tools import AnalysisTools

logger = logging.getLogger(__name__)


class UseCaseGenerationAgent:
    """Agent for generating AI and GenAI use cases."""

    def __init__(self, llm: LLMInterface, analysis_tools: AnalysisTools):
        """Initialize the use case generation agent.

        Args:
            llm: LLM interface for generating analysis.
            analysis_tools: Tools for analyzing information.
        """
        self.llm = llm
        self.analysis_tools = analysis_tools

    async def generate_use_cases(
        self,
        company_info: Dict[str, Any],
        industry_info: Dict[str, Any],
        num_use_cases: int = 5,
    ) -> List[Dict[str, Any]]:
        """Generate AI and GenAI use cases for a company.

        Args:
            company_info: Information about the company.
            industry_info: Information about the industry.
            num_use_cases: Number of use cases to generate.

        Returns:
            List of use case dictionaries.
        """
        logger.info(f"Generating use cases for {company_info.get('name', 'company')}")

        # Extract use cases
        use_cases = await self.analysis_tools.extract_use_cases(
            company_info=company_info,
            industry_info=industry_info,
            num_use_cases=num_use_cases,
        )

        # Prioritize use cases
        prioritized_use_cases = await self.analysis_tools.prioritize_use_cases(
            use_cases=use_cases, company_info=company_info
        )

        # Add use case keywords for resource retrieval
        await self._add_keywords(prioritized_use_cases)

        return prioritized_use_cases

    async def _add_keywords(self, use_cases: List[Dict[str, Any]]) -> None:
        """Add relevant keywords to each use case for resource retrieval.

        Args:
            use_cases: List of use case dictionaries.
        """
        if not use_cases:
            return

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
        
        USE CASES: {use_cases_text}
        
        For each use case, include specific technical terms, industry-specific terminology, and relevant AI model types that would yield good search results.
        
        """

        system_prompt = """
        
        You are a technical research specialist who identifies precise, relevant keywords for AI and ML research and resource discovery. You have deep knowledge of AI terminology, datasets, and implementation resources.
        
        """

        try:
            # Generate keywords using the LLM
            result = await self.llm.generate_with_json_output(
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

            for uc in use_cases:
                title = uc.get("title", "")
                if title in keyword_map:
                    uc["keywords"] = keyword_map[title]
                else:
                    # If no keywords found, extract from AI technologies
                    uc["keywords"] = uc.get("ai_technologies", [])

        except Exception as e:
            logger.error(f"Error adding keywords to use cases: {e}")
            # Ensure all use cases have at least some keywords
            for uc in use_cases:
                if "keywords" not in uc:
                    uc["keywords"] = uc.get("ai_technologies", [])
