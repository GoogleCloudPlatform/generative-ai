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

"""Primary RAG pipeline: Agent Search over a PUBLIC_WEBSITE data store.

The recommended setup for an ISV:
    1. Admin runs scripts/provision_engine.py with their docs URL.
    2. That creates a PUBLIC_WEBSITE data store with advanced indexing,
       attaches the engine with SEARCH_TIER_ENTERPRISE + SEARCH_ADD_ON_LLM,
       and registers the engine path against the tenant.
    3. This pipeline queries that engine, returning extractive answers
       plus the LLM-generated summary with inline citations.

Uses the v1 servingConfig path (`default_search`). Falls back to snippets
when extractive answers aren't available; falls back to summary when
neither is present.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import google.auth
import google.auth.transport.requests
import httpx

from .base import RetrievedDoc

logger = logging.getLogger(__name__)

DEFAULT_SEARCH_TIMEOUT_S = 12.0


class WebsiteSearchPipeline:
    """Agent Search (Discovery Engine) over a website data store."""

    name = "website"

    def __init__(self, engine_path: str, location: str = "global"):
        """Initialize with engine resource path.

        Args:
            engine_path: Full resource path like
                "projects/123/locations/global/collections/default_collection/engines/my-engine"
            location: Discovery Engine location; "global" for website data stores.
        """
        self.engine_path = engine_path
        self.location = location
        self.endpoint = (
            f"https://discoveryengine.googleapis.com/v1/"
            f"{engine_path}/servingConfigs/default_search:search"
        )
        self._explicit_token = os.environ.get("VERTEX_SEARCH_TOKEN", "").strip() or None
        self._credentials: Any = None
        self._auth_request: Any = None

    def _get_token(self) -> str:
        if self._explicit_token:
            return self._explicit_token
        if self._credentials is None:
            self._credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            self._auth_request = google.auth.transport.requests.Request()
        # Only hit the token endpoint when the cached token is missing/expired.
        if not self._credentials.valid:
            self._credentials.refresh(self._auth_request)
        return self._credentials.token

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDoc]:
        """Search the engine. Returns ranked, deduplicated docs."""
        if not query.strip():
            return []

        payload = {
            "query": query,
            "pageSize": min(top_k, 10),
            "queryExpansionSpec": {"condition": "AUTO"},
            "spellCorrectionSpec": {"mode": "AUTO"},
            "contentSearchSpec": {
                "snippetSpec": {"returnSnippet": True},
                "extractiveContentSpec": {
                    "maxExtractiveAnswerCount": 1,
                    "maxExtractiveSegmentCount": 1,
                },
                "summarySpec": {
                    "summaryResultCount": min(top_k, 5),
                    "includeCitations": True,
                    "ignoreAdversarialQuery": True,
                },
            },
        }
        try:
            resp = httpx.post(
                self.endpoint,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._get_token()}",
                    "Content-Type": "application/json",
                },
                timeout=DEFAULT_SEARCH_TIMEOUT_S,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught  # search failures return no docs
            logger.error("WebsiteSearchPipeline query failed: %s", e)
            return []

        return self._parse_response(data, top_k)

    def _parse_response(  # pylint: disable=too-many-locals
        self, data: dict, top_k: int
    ) -> list[RetrievedDoc]:
        docs: list[RetrievedDoc] = []

        # First: include the LLM-generated summary as its own doc so the
        # agent has a coherent starting point with citations baked in.
        summary = data.get("summary", {}) or {}
        summary_text = summary.get("summaryText", "")
        if summary_text:
            cites: list[str] = []
            for cite in (
                summary.get("summaryWithMetadata", {})
                .get("citationMetadata", {})
                .get("citations", [])
            ):
                for src in cite.get("sources", []):
                    ref_index = src.get("referenceIndex")
                    if ref_index is not None:
                        cites.append(str(ref_index))
            docs.append(
                RetrievedDoc(
                    title="Summary",
                    content=summary_text,
                    pipeline=self.name,
                    citations=cites,
                )
            )

        # Then: individual results with their extractive answers / snippets.
        for result in data.get("results", []):
            doc = result.get("document", {}) or {}
            derived = doc.get("derivedStructData", {}) or {}
            title = derived.get("title") or doc.get("name") or "Untitled"
            link = derived.get("link", "")

            content = ""
            answers = derived.get("extractive_answers") or []
            if answers:
                content = answers[0].get("content", "")
            if not content:
                segments = derived.get("extractive_segments") or []
                if segments:
                    content = segments[0].get("content", "")
            if not content:
                snippets = derived.get("snippets") or []
                content = snippets[0].get("snippet", "") if snippets else ""
            if not content:
                content = link  # last resort

            score = 0.0
            scores = result.get("modelScores", {}) or {}
            rel = scores.get("relevance_score", {}) or {}
            vals = rel.get("values", []) or []
            if vals:
                score = float(vals[0])

            docs.append(
                RetrievedDoc(
                    title=title,
                    content=content,
                    source_url=link,
                    relevance_score=score,
                    pipeline=self.name,
                )
            )
            if len(docs) >= top_k + 1:  # +1 to keep the summary
                break

        return docs
