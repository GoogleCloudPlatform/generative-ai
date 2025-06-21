import logging
from typing import Any, Dict, List, Optional, Tuple

from langchain.schema import AIMessage, HumanMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from models.llm_interface import LLMInterface
from tools.search_tools import SearchTools

logger = logging.getLogger(__name__)


def create_research_workflow(llm: LLMInterface, search_tools: SearchTools):
    """Create a workflow for researching company and industry information.

    Args:
        llm: LLM interface for generating analysis.
        search_tools: Tools for searching the web.

    Returns:
        A workflow function.
    """

    async def research_company(state: Dict[str, Any]) -> Dict[str, Any]:
        """Research company information."""
        company_name = state.get("company_name")
        if not company_name:
            return {"company_info": {}}

        try:
            logger.info(f"Researching company: {company_name}")
            company_info = await search_tools.search_company_info(company_name)
            return {"company_info": company_info}
        except Exception as e:
            logger.error(f"Error researching company: {e}")
            return {"company_info": {}, "error": str(e)}

    async def research_industry(state: Dict[str, Any]) -> Dict[str, Any]:
        """Research industry information."""
        industry_name = state.get("industry_name")

        # If industry name not provided, try to extract from company info
        if not industry_name and "company_info" in state:
            company_info = state["company_info"]
            if company_info and "industry" in company_info:
                industry_name = company_info["industry"]

        if not industry_name:
            return {"industry_info": {}}

        try:
            logger.info(f"Researching industry: {industry_name}")
            industry_info = await search_tools.search_industry_info(industry_name)
            return {"industry_info": industry_info}
        except Exception as e:
            logger.error(f"Error researching industry: {e}")
            return {"industry_info": {}, "error": str(e)}

    async def enhance_research(state: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance research with additional insights."""
        company_info = state.get("company_info", {})
        industry_info = state.get("industry_info", {})

        # Skip if no information is available
        if not company_info and not industry_info:
            return {}

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
2. Areas where AI and Gen AI could provide significant value
3. Industry-specific considerations for AI implementation
4. Potential data sources within such companies that could be leveraged for AI

Format your response as a structured analysis with clear sections.
"""

        system_prompt = """
You are an industry research analyst specializing in technology adoption trends and AI implementation opportunities. You synthesize information about companies and industries to identify key insights that would be valuable for AI strategy planning.
"""

        try:
            # Generate enhanced insights
            insights = await llm.generate(
                prompt=prompt, system_prompt=system_prompt, temperature=0.4
            )

            # Add insights to company and industry information
            enhanced_info = {}
            if company_info:
                enhanced_company_info = company_info.copy()
                enhanced_company_info["enhanced_insights"] = insights
                enhanced_info["company_info"] = enhanced_company_info

            if industry_info:
                enhanced_industry_info = industry_info.copy()
                enhanced_industry_info["enhanced_insights"] = insights
                enhanced_info["industry_info"] = enhanced_industry_info

            return enhanced_info

        except Exception as e:
            logger.error(f"Error enhancing research: {e}")
            return {}

    # Define the research workflow
    async def research_workflow(input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the research workflow."""
        state = input_data.copy()

        # Step 1: Research company
        if "company_name" in state and state["company_name"]:
            company_result = await research_company(state)
            state.update(company_result)

        # Step 2: Research industry
        if (
            "industry_name" in state
            and state["industry_name"]
            or "company_info" in state
        ):
            industry_result = await research_industry(state)
            state.update(industry_result)

        # Step 3: Enhance research
        if "company_info" in state or "industry_info" in state:
            enhanced_result = await enhance_research(state)
            state.update(enhanced_result)

        return state

    return research_workflow
