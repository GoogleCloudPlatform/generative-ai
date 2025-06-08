import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from langchain_community.utilities import SerpAPIWrapper

from config.settings import SEARCH_CONFIG, SERPAPI_KEY

logger = logging.getLogger(__name__)


class SearchTools:
    """Tools for searching the web for information."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the search tools.

        Args:
            api_key: Optional API key for SerpAPI.
        """
        self.api_key = api_key or SERPAPI_KEY
        if not self.api_key:
            raise ValueError("SerpAPI key is required")

        self.max_results = SEARCH_CONFIG["max_results"]
        self.timeout = SEARCH_CONFIG["timeout"]

        # Initialize SerpAPI wrapper
        self.serpapi = SerpAPIWrapper(serpapi_api_key=self.api_key)

    async def search(
        self, query: str, num_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search the web for information.

        Args:
            query: The search query.
            num_results: Optional number of results to return.

        Returns:
            List of search result dictionaries.
        """
        num_results = num_results or self.max_results

        try:
            logger.info(f"Searching for: {query}")

            # Updated to match the SerpAPIWrapper API
            # The results method only takes the query parameter
            results = await asyncio.to_thread(self.serpapi.results, query)

            # Extract organic results
            organic_results = []
            if "organic_results" in results:
                for result in results["organic_results"][:num_results]:
                    organic_results.append(
                        {
                            "title": result.get("title", ""),
                            "link": result.get("link", ""),
                            "snippet": result.get("snippet", ""),
                            "source": "serpapi",
                        }
                    )

            logger.info(f"Found {len(organic_results)} results for query: {query}")
            return organic_results

        except Exception as e:
            logger.error(f"Error during web search: {e}")
            return []

    async def search_company_info(self, company_name: str) -> Dict[str, Any]:
        """Search for information about a company.

        Args:
            company_name: The name of the company.

        Returns:
            Dictionary with company information.
        """
        company_info = {
            "name": company_name,
            "description": "",
            "industry": "",
            "products": [],
            "url": "",
            "competitors": [],
        }

        try:
            # Search for company information
            results = await self.search(f"{company_name} company information")

            if results:
                # Extract basic company information from the first result
                company_info["description"] = results[0].get("snippet", "")
                company_info["url"] = results[0].get("link", "")

            # Search for company products
            product_results = await self.search(f"{company_name} products services")
            if product_results:
                product_snippets = [
                    result.get("snippet", "") for result in product_results[:3]
                ]
                company_info["products"] = product_snippets

            # Search for company industry
            industry_results = await self.search(f"{company_name} industry sector")
            if industry_results:
                company_info["industry"] = industry_results[0].get("snippet", "")

            # Search for competitors
            competitor_results = await self.search(f"{company_name} competitors")
            if competitor_results:
                company_info["competitors"] = [
                    result.get("title", "").replace(" - Wikipedia", "")
                    for result in competitor_results[:5]
                ]

            return company_info

        except Exception as e:
            logger.error(f"Error retrieving company information: {e}")
            return company_info

    async def search_industry_info(self, industry_name: str) -> Dict[str, Any]:
        """Search for information about an industry.

        Args:
            industry_name: The name of the industry.

        Returns:
            Dictionary with industry information.
        """
        industry_info = {
            "name": industry_name,
            "description": "",
            "trends": [],
            "challenges": [],
            "major_players": [],
            "ai_applications": [],
        }

        try:
            # Search for industry description
            results = await self.search(f"{industry_name} industry overview")

            if results:
                # Extract industry description from the first result
                industry_info["description"] = results[0].get("snippet", "")

            # Search for industry trends
            trend_results = await self.search(f"{industry_name} industry trends 2025")
            if trend_results:
                industry_info["trends"] = [
                    result.get("snippet", "") for result in trend_results[:3]
                ]

            # Search for industry challenges
            challenge_results = await self.search(
                f"{industry_name} industry challenges problems"
            )
            if challenge_results:
                industry_info["challenges"] = [
                    result.get("snippet", "") for result in challenge_results[:3]
                ]

            # Search for major players
            player_results = await self.search(
                f"top companies in {industry_name} industry"
            )
            if player_results:
                industry_info["major_players"] = [
                    result.get("title", "").split(" - ")[0]
                    for result in player_results[:5]
                ]

            # Search for AI applications in the industry
            ai_results = await self.search(
                f"artificial intelligence applications in {industry_name} industry"
            )
            if ai_results:
                industry_info["ai_applications"] = [
                    result.get("snippet", "") for result in ai_results[:3]
                ]

            return industry_info

        except Exception as e:
            logger.error(f"Error retrieving industry information: {e}")
            return industry_info
