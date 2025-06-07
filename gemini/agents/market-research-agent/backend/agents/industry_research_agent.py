import logging
from typing import Any, Dict, Optional, Tuple

from models.llm_interface import LLMInterface
from tools.search_tools import SearchTools

logger = logging.getLogger(__name__)


class IndustryResearchAgent:
    """Agent for researching industries and generating use cases."""

    def __init__(self, llm: LLMInterface, search_tools: SearchTools):
        """Initialize the industry research agent.

        Args:
            llm: LLM interface for generating analysis.
            search_tools: Tools for searching the web.
        """
        self.llm = llm
        self.search_tools = search_tools

    async def research(
        self, company_name: Optional[str] = None, industry_name: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Research a company and its industry.

        Args:
            company_name: Optional name of the company.
            industry_name: Optional name of the industry.

        Returns:
            Tuple containing company information and industry information dictionaries.
        """
        logger.info(f"Researching company: {company_name}, industry: {industry_name}")

        company_info = {}
        industry_info = {}

        # Research company if provided
        if company_name:
            company_info = await self.search_tools.search_company_info(company_name)

            # If industry not provided, extract it from company info
            if not industry_name and company_info.get("industry"):
                industry_name = company_info.get("industry")

        # Research industry if available
        if industry_name:
            industry_info = await self.search_tools.search_industry_info(industry_name)

        # Enhance research with additional insights
        await self._enhance_research(company_info, industry_info)

        return company_info, industry_info

    async def _enhance_research(
        self, company_info: Dict[str, Any], industry_info: Dict[str, Any]
    ) -> None:
        """Enhance research with additional insights using the LLM.

        Args:
            company_info: Information about the company.
            industry_info: Information about the industry.
        """
        # Skip if no information is available
        if not company_info and not industry_info:
            return

        # Prepare prompt for enhancement
        prompt = "Based on the following information, provide additional insights and structured analysis:\n\n"

        if company_info:
            prompt += f"COMPANY INFORMATION:\n"
            prompt += f"Name: {company_info.get('name', 'Unknown')}\n"
            prompt += f"Description: {company_info.get('description', '')}\n"
            prompt += f"Industry: {company_info.get('industry', '')}\n"
            prompt += (
                f"Products/Services: {', '.join(company_info.get('products', []))}\n"
            )
            prompt += (
                f"Competitors: {', '.join(company_info.get('competitors', []))}\n\n"
            )

        if industry_info:
            prompt += f"INDUSTRY INFORMATION:\n"
            prompt += f"Name: {industry_info.get('name', 'Unknown')}\n"
            prompt += f"Description: {industry_info.get('description', '')}\n"
            prompt += f"Trends: {' '.join(industry_info.get('trends', []))}\n"
            prompt += f"Challenges: {' '.join(industry_info.get('challenges', []))}\n"
            prompt += (
                f"Major Players: {', '.join(industry_info.get('major_players', []))}\n"
            )
            prompt += f"AI Applications: {' '.join(industry_info.get('ai_applications', []))}\n\n"

        prompt += """Provide additional insights in the following areas:
        1. Key operational challenges faced by companies in this industry
        2. Areas where AI and GenAI could provide significant value
        3. Industry-specific considerations for AI implementation
        4. Potential data sources within such companies that could be leveraged for AI

        Format your response as a structured analysis with clear sections.
        """

        system_prompt = """
        You are an industry research analyst specializing in technology adoption trends and AI implementation opportunities. You synthesize information about companies and industries to identify key insights that would be valuable for AI strategy planning.
        """

        try:
            # Generate enhanced insights
            insights = await self.llm.generate(
                prompt=prompt, system_prompt=system_prompt, temperature=0.4
            )

            # Add insights to company and industry information
            if company_info:
                company_info["enhanced_insights"] = insights
            elif industry_info:
                industry_info["enhanced_insights"] = insights

        except Exception as e:
            logger.error(f"Error enhancing research: {e}")
