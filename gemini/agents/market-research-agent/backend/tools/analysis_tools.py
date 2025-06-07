import logging
from typing import Any, Dict, List, Optional

from models.llm_interface import LLMInterface

logger = logging.getLogger(__name__)


class AnalysisTools:
    """Tools for analyzing information and generating insights."""

    def __init__(self, llm: LLMInterface):
        """Initialize the analysis tools.

        Args:
            llm: LLM interface for generating analysis.
        """
        self.llm = llm

    async def extract_use_cases(
        self,
        company_info: Dict[str, Any],
        industry_info: Dict[str, Any],
        num_use_cases: int = 5,
    ) -> List[Dict[str, Any]]:
        """Extract potential AI use cases from company and industry information.

        Args:
            company_info: Information about the company.
            industry_info: Information about the industry.
            num_use_cases: Number of use cases to generate.

        Returns:
            List of use case dictionaries.
        """
        # Define the JSON schema for use cases
        use_case_schema = {
            "type": "object",
            "properties": {
                "use_cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "business_value": {"type": "string"},
                            "implementation_complexity": {
                                "type": "string",
                                "enum": ["Low", "Medium", "High"],
                            },
                            "ai_technologies": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "industry": {"type": "string"},
                            "keywords": {"type": "array", "items": {"type": "string"}},
                            "cross_functional_benefits": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "department": {"type": "string"},
                                        "benefit": {"type": "string"},
                                    },
                                },
                            },
                        },
                        "required": [
                            "title",
                            "description",
                            "business_value",
                            "implementation_complexity",
                            "ai_technologies",
                        ],
                    },
                }
            },
            "required": ["use_cases"],
        }

        # Create the prompt for use case extraction
        prompt = f"""
        You are an AI expert in Analyze the following information about a company and its industry to identify potential AI and GenAI use cases:

        Company Information:
            - Name: {company_info.get("name", "Unknown")}
            - Description: {company_info.get("description", "")}
            - Industry: {company_info.get("industry", "")}
            - Products/Services: {", ".join(company_info.get("products", []))}
            - Competitors: {", ".join(company_info.get("competitors", []))}

        INDUSTRY INFORMATION:
            - Industry Name: {industry_info.get("name", "Unknown")}
            - Description: {industry_info.get("description", "")}
            - Trends: {" ".join(industry_info.get("trends", []))}
            - Challenges: {" ".join(industry_info.get("challenges", []))}
            - Major Players: {", ".join(industry_info.get("major_players", []))}
            - Existing AI Applications: {" ".join(industry_info.get("ai_applications", []))}

        Generate {num_use_cases} high-value, innovative AI and GenAI use cases that would benefit this company, focusing on:
            1. Business operations improvement
            2. Customer experience enhancement
            3. Product/service innovation
            4. Cost reduction and efficiency
            5. Competitive advantage

        For each use case, include a descriptive title, detailed description, business value proposition, implementation complexity (Low/Medium/High), relevant AI technologies (e.g., LLMs, computer vision, predictive analytics), and cross-functional benefits.

        Focus on practical, implementable use cases with clear business value rather than theoretical applications.
        """

        system_prompt = """
        You are an AI strategy consultant specializing in identifying high-value AI and GenAI implementation opportunities for companies across various industries. Your expertise includes understanding business operations, market dynamics, and how AI technologies can address specific challenges and create competitive advantages.
        """

        try:
            # Generate use cases using the LLM
            result = await self.llm.generate_with_json_output(
                prompt=prompt,
                json_schema=use_case_schema,
                system_prompt=system_prompt,
                temperature=0.7,  # Higher temperature for more creative use cases
            )

            use_cases = result.get("use_cases", [])
            logger.info(f"Generated {len(use_cases)} use cases")

            return use_cases

        except Exception as e:
            logger.error(f"Error extracting use cases: {e}")
            return []

    async def prioritize_use_cases(
        self, use_cases: List[Dict[str, Any]], company_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Prioritize use cases based on company needs and implementation feasibility.

        Args:
            use_cases: List of use case dictionaries.
            company_info: Information about the company.

        Returns:
            Prioritized list of use case dictionaries.
        """
        if not use_cases:
            return []

        # Define the JSON schema for prioritized use cases
        prioritization_schema = {
            "type": "object",
            "properties": {
                "prioritized_use_cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "priority_score": {
                                "type": "number",
                                "minimum": 1,
                                "maximum": 10,
                            },
                            "rationale": {"type": "string"},
                        },
                        "required": ["title", "priority_score", "rationale"],
                    },
                }
            },
            "required": ["prioritized_use_cases"],
        }

        # Create the prompt for use case prioritization
        use_cases_text = "\n\n".join(
            [
                f"USE CASE {i + 1}: {uc.get('title', '')}\n"
                + f"Description: {uc.get('description', '')}\n"
                + f"Business Value: {uc.get('business_value', '')}\n"
                + f"Implementation Complexity: {uc.get('implementation_complexity', 'Unknown')}\n"
                + f"AI Technologies: {', '.join(uc.get('ai_technologies', []))}"
                for i, uc in enumerate(use_cases)
            ]
        )

        prompt = f"""
        Review and prioritize the following AI and GenAI use cases for {company_info.get("name", "this company")} in the {company_info.get("industry", "")} industry.

        COMPANY INFORMATION:
            - Description: {company_info.get("description", "")}
            - Products/Services: {", ".join(company_info.get("products", []))}

        USE CASES:
        {use_cases_text}

        For each use case, provide:
            1. A priority score (1-10, with 10 being highest priority)
            2. A rationale for the assigned priority score based on:
                - Potential business impact
                - Implementation feasibility
                - Alignment with industry trends
                - Competitive advantage
                - ROI potential

        Focus on practical value and realistic implementation, not just technological novelty.
    
    """

        system_prompt = """
        You are an AI implementation strategist who helps companies prioritize AI and GenAI initiatives based on business value, feasibility, and strategic alignment. You have extensive experience in technology roadmapping and resource allocation for AI projects.
        """

        try:
            # Generate prioritization using the LLM
            result = await self.llm.generate_with_json_output(
                prompt=prompt,
                json_schema=prioritization_schema,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more consistent prioritization
            )

            prioritized_cases = result.get("prioritized_use_cases", [])
            logger.info(f"Prioritized {len(prioritized_cases)} use cases")

            # Match prioritization with original use cases and sort by priority score
            priority_map = {
                pc["title"]: pc["priority_score"] for pc in prioritized_cases
            }
            rationale_map = {pc["title"]: pc["rationale"] for pc in prioritized_cases}

            for uc in use_cases:
                title = uc.get("title", "")
                uc["priority_score"] = priority_map.get(
                    title, 5
                )  # Default to middle priority
                uc["prioritization_rationale"] = rationale_map.get(title, "")

            # Sort use cases by priority score (descending)
            sorted_use_cases = sorted(
                use_cases, key=lambda x: x.get("priority_score", 0), reverse=True
            )

            return sorted_use_cases

        except Exception as e:
            logger.error(f"Error prioritizing use cases: {e}")
            return use_cases  # Return original use cases if prioritization fails
