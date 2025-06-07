import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from kaggle.api.kaggle_api_extended import KaggleApi

from config.settings import (DATASET_CONFIG, HUGGINGFACE_API_KEY, KAGGLE_KEY,
                             KAGGLE_USERNAME)

logger = logging.getLogger(__name__)


class DatasetTools:
    """Tools for finding and analyzing datasets."""

    def __init__(self):
        """Initialize the dataset tools."""
        self.sources = DATASET_CONFIG["sources"]
        self.max_results_per_source = DATASET_CONFIG["max_results_per_source"]
        self.timeout = DATASET_CONFIG["timeout"]

        # Set up Kaggle credentials
        if KAGGLE_USERNAME and KAGGLE_KEY:
            os.environ["KAGGLE_USERNAME"] = KAGGLE_USERNAME
            os.environ["KAGGLE_KEY"] = KAGGLE_KEY
            self.kaggle_available = True
            try:
                self.kaggle_api = KaggleApi()
                self.kaggle_api.authenticate()
            except Exception as e:
                logger.error(f"Failed to authenticate with Kaggle: {e}")
                self.kaggle_available = False
        else:
            logger.warning("Kaggle credentials not found")
            self.kaggle_available = False

        # Check for HuggingFace credentials
        self.huggingface_api_key = HUGGINGFACE_API_KEY
        self.huggingface_available = bool(self.huggingface_api_key)
        if not self.huggingface_available:
            logger.warning("HuggingFace API key not found")

    async def search_kaggle_datasets(
        self, query: str, max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for datasets on Kaggle.

        Args:
            query: The search query.
            max_results: Optional maximum number of results to return.

        Returns:
            List of dataset information dictionaries.
        """
        max_results = max_results or self.max_results_per_source

        if not self.kaggle_available:
            logger.warning("Kaggle API not available")
            return []

        try:
            logger.info(f"Searching Kaggle for datasets: {query}")

            # Search for datasets
            datasets = await asyncio.to_thread(
                self.kaggle_api.dataset_list,
                search=query,
                sort_by="relevance",
                max_size=None,
                file_type=None,
                license_name=None,
                tag_ids=None,
            )

            # Extract dataset information
            results = []
            for dataset in datasets:
                results.append(
                    {
                        "title": dataset.title,
                        "name": dataset.ref,
                        "url": f"https://www.kaggle.com/datasets/{dataset.ref}",
                        "description": dataset.description,
                        "source": "kaggle",
                        "size": dataset.size,
                        "last_updated": dataset.lastUpdated,
                        "download_count": dataset.downloadCount,
                    }
                )

            logger.info(f"Found {len(results)} Kaggle datasets for query: {query}")
            return results[:max_results]

        except Exception as e:
            logger.error(f"Error searching Kaggle datasets: {e}")
            return []

    async def search_huggingface_datasets(
        self, query: str, max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for datasets on HuggingFace.

        Args:
            query: The search query.
            max_results: Optional maximum number of results to return.

        Returns:
            List of dataset information dictionaries.
        """
        max_results = max_results or self.max_results_per_source

        if not self.huggingface_available:
            logger.warning("HuggingFace API not available")
            return []

        try:
            logger.info(f"Searching HuggingFace for datasets: {query}")

            # Search HuggingFace API
            headers = {}
            if self.huggingface_api_key:
                headers["Authorization"] = f"Bearer {self.huggingface_api_key}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://huggingface.co/api/datasets",
                    params={"search": query, "limit": max_results},
                    headers=headers,
                )
                response.raise_for_status()
                datasets = response.json()

            # Extract dataset information
            results = []
            for dataset in datasets:
                results.append(
                    {
                        "title": dataset.get("id", ""),
                        "name": dataset.get("id", ""),
                        "url": f"https://huggingface.co/datasets/{dataset.get('id', '')}",
                        "description": dataset.get("description", ""),
                        "source": "huggingface",
                        "author": dataset.get("author", ""),
                        "tags": dataset.get("tags", []),
                    }
                )

            logger.info(f"Found {len(results)} HuggingFace datasets for query: {query}")
            return results[:max_results]

        except Exception as e:
            logger.error(f"Error searching HuggingFace datasets: {e}")
            return []

    async def search_github_datasets(
        self, query: str, max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for datasets on GitHub.

        Args:
            query: The search query.
            max_results: Optional maximum number of results to return.

        Returns:
            List of dataset information dictionaries.
        """
        max_results = max_results or self.max_results_per_source

        try:
            logger.info(f"Searching GitHub for datasets: {query}")

            # Search GitHub API
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://api.github.com/search/repositories",
                    params={
                        "q": f"{query} dataset",
                        "sort": "stars",
                        "order": "desc",
                        "per_page": max_results,
                    },
                )
                response.raise_for_status()
                data = response.json()

                repositories = data.get("items", [])

            # Extract repository information
            results = []
            for repo in repositories:
                results.append(
                    {
                        "title": repo.get("name", ""),
                        "name": repo.get("full_name", ""),
                        "url": repo.get("html_url", ""),
                        "description": repo.get("description", ""),
                        "source": "github",
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "last_updated": repo.get("updated_at", ""),
                    }
                )

            logger.info(f"Found {len(results)} GitHub repositories for query: {query}")
            return results[:max_results]

        except Exception as e:
            logger.error(f"Error searching GitHub repositories: {e}")
            return []

    async def search_datasets(
        self, query: str, sources: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Search for datasets across multiple sources.

        Args:
            query: The search query.
            sources: Optional list of sources to search.

        Returns:
            Dictionary mapping source names to lists of dataset information.
        """
        # Use default sources if none provided
        sources = sources or self.sources

        # Filter unavailable sources
        available_sources = []
        if "kaggle" in sources and self.kaggle_available:
            available_sources.append("kaggle")
        if "huggingface" in sources and self.huggingface_available:
            available_sources.append("huggingface")
        if "github" in sources:
            available_sources.append("github")

        if not available_sources:
            logger.warning("No available dataset sources found")
            return {}

        sources = available_sources
        results = {}

        search_coroutines = []
        source_names = []

        # Add search coroutines for each source
        if "kaggle" in sources:
            search_coroutines.append(self.search_kaggle_datasets(query))
            source_names.append("kaggle")

        if "huggingface" in sources:
            search_coroutines.append(self.search_huggingface_datasets(query))
            source_names.append("huggingface")

        if "github" in sources:
            search_coroutines.append(self.search_github_datasets(query))
            source_names.append("github")

        if not search_coroutines:
            return {}

        # Run searches in parallel
        all_results = await asyncio.gather(*search_coroutines, return_exceptions=True)

        # Process results
        for i, source in enumerate(source_names):
            if i < len(all_results):
                if isinstance(all_results[i], Exception):
                    logger.error(f"Error searching {source}: {all_results[i]}")
                    results[source] = []
                else:
                    results[source] = all_results[i]

        return results

    async def find_datasets_for_use_case(
        self, use_case: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find datasets relevant to a specific use case.

        Args:
            use_case: Dictionary describing the use case.

        Returns:
            List of relevant datasets.
        """
        if not use_case:
            logger.warning("Empty use case provided to find_datasets_for_use_case")
            return []

        title = use_case.get("title", "")
        description = use_case.get("description", "")

        if not title and not description:
            logger.warning("Use case has no title or description")
            return []

        # Generate search queries based on use case
        queries = []
        if title:
            queries.extend([title, f"{title} dataset", f"{title} machine learning"])

        if "industry" in use_case and use_case["industry"]:
            queries.append(f"{use_case['industry']} {title} dataset")

        if (
            "keywords" in use_case
            and isinstance(use_case["keywords"], list)
            and use_case["keywords"]
        ):
            for keyword in use_case["keywords"][:2]:  # Limit to top 2 keywords
                if keyword:
                    queries.append(f"{keyword} dataset")

        # Ensure we have at least one query
        if not queries:
            logger.warning(
                "No valid search queries could be generated for the use case"
            )
            return []

        # Search for datasets using each query
        all_datasets = []
        for query in queries:
            try:
                source_results = await self.search_datasets(query)

                # Flatten results from all sources (handle case where source_results is None)
                if not source_results:
                    continue

                for source, datasets in source_results.items():
                    if not datasets:
                        continue

                    for dataset in datasets:
                        # Add the query that found this dataset
                        dataset["query"] = query
                        all_datasets.append(dataset)
            except Exception as e:
                logger.error(f"Error searching datasets for query '{query}': {e}")

        # Deduplicate datasets based on URL
        unique_datasets = {}
        for dataset in all_datasets:
            url = dataset.get("url", "")
            if url and url not in unique_datasets:
                unique_datasets[url] = dataset

        return list(unique_datasets.values())
