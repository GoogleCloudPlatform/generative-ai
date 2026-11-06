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

"""Common RAG types and the pipeline interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class RetrievedDoc:
    """One grounded document returned by a RAG pipeline."""

    title: str
    content: str
    source_url: str = ""
    relevance_score: float = 0.0
    pipeline: str = ""
    citations: list[str] = field(default_factory=list)

    def to_payload(self) -> dict:
        return {
            "title": self.title,
            "content": self.content,
            "source_url": self.source_url,
            "relevance_score": self.relevance_score,
            "pipeline": self.pipeline,
            "citations": self.citations,
        }


class RagPipeline(Protocol):
    """Minimal interface a RAG backend must satisfy."""

    name: str

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDoc]: ...


class NullPipeline:
    """No-op pipeline. Used when a tenant has nothing configured."""

    name = "null"

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDoc]:
        return []
