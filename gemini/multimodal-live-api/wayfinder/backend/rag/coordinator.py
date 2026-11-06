# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Coordinator that routes a query across the configured RAG pipelines.

`search()` queries pipelines in order and returns the first non-empty result.
`asearch_payload()` runs it off the event loop, and `build_adk_tool()` wraps
it as the `search_knowledge_base` ADK tool. Today the only pipeline is Vertex
AI Search (`WebsiteSearchPipeline`), which works for website and document
data stores; add more pipelines by implementing `RagPipeline`.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable

from .base import NullPipeline, RagPipeline, RetrievedDoc
from .website_pipeline import WebsiteSearchPipeline

logger = logging.getLogger(__name__)


class RagCoordinator:
    """Fan-out / fall-through over configured RAG pipelines."""

    def __init__(self, pipelines: Iterable[RagPipeline]):
        self.pipelines: list[RagPipeline] = [p for p in pipelines if p is not None]
        if not self.pipelines:
            self.pipelines = [NullPipeline()]

    @property
    def pipeline_names(self) -> list[str]:
        """Names of the configured pipelines, in query order."""
        return [p.name for p in self.pipelines]

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDoc]:
        """Query pipelines in order, fall through on empty."""
        for pipeline in self.pipelines:
            try:
                results = pipeline.search(query, top_k=top_k)
            except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught  # fall through to the next pipeline
                logger.error("Pipeline %s raised: %s", pipeline.name, e)
                continue
            if results:
                logger.info(
                    "Pipeline %s returned %d docs for %r",
                    pipeline.name,
                    len(results),
                    query[:60],
                )
                return results
        logger.info("All pipelines empty for %r", query[:60])
        return []

    def search_payload(self, query: str, top_k: int = 5) -> dict:
        """Tool-response shaped dict for direct injection into Live API."""
        docs = self.search(query, top_k=top_k)
        if not docs:
            return {
                "found": False,
                "message": f"No documentation found for '{query}'.",
                "pipelines_queried": self.pipeline_names,
            }
        return {
            "found": True,
            "count": len(docs),
            "documents": [d.to_payload() for d in docs],
            "pipelines_queried": self.pipeline_names,
        }

    async def asearch_payload(self, query: str, top_k: int = 5) -> dict:
        """Async wrapper: pipelines use blocking HTTP, so run them off the
        event loop. Keeps voice/text sessions responsive during a search.
        """
        return await asyncio.to_thread(self.search_payload, query, top_k)

    def build_adk_tool(self) -> object:
        """Return an ADK FunctionTool wrapping `search`.

        Imported lazily so the ADK dependency is only required by paths
        that actually use it (text/HTTP runner).
        """
        from google.adk.tools import (  # pylint: disable=import-outside-toplevel
            FunctionTool,
        )

        async def search_knowledge_base(query: str) -> dict:
            """Search the customer's documentation for an answer to the query."""
            return await self.asearch_payload(query, top_k=5)

        return FunctionTool(func=search_knowledge_base)


def build_coordinator_for_tenant(
    website_engine_path: str | None = None,
) -> RagCoordinator:
    """Construct a coordinator from per-tenant config."""
    pipelines: list[RagPipeline] = []
    if website_engine_path:
        pipelines.append(WebsiteSearchPipeline(website_engine_path))
    return RagCoordinator(pipelines)
