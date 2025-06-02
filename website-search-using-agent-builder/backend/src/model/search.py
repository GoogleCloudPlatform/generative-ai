# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Defines data models for search operations and configurations.

This module includes Pydantic models for API requests/responses related to
search applications and engines, as well as dataclasses for representing
search results internally. It also handles fetching the default Google Cloud
Project ID.
"""

from dataclasses import dataclass
from typing import List, Optional
from pydantic import BaseModel
from google.cloud.bigquery import SchemaField, Row
from google.api_core.client_options import ClientOptions
import google.auth

_, PROJECT_ID = google.auth.default()


class CreateSearchRequest(BaseModel):
    """Request model for initiating a search."""
    term: str


class SearchApplication(BaseModel):
    """Represents the configuration for a Discovery Engine
    Search Application."""
    engine_id: str
    region: str

    @classmethod
    def __schema__(cls) -> List[SchemaField]:
        """Defines the BigQuery schema for storing SearchApplication data."""
        return [
            SchemaField("engine_id", "STRING", mode="REQUIRED"),
            SchemaField("region", "STRING", mode="REQUIRED"),
        ]

    @classmethod
    def from_row(cls, row: Row) -> 'SearchApplication':
        """Creates a SearchApplication instance from a BigQuery Row object.

        Args:
            row: The BigQuery Row object. Assumes row contains fields matching the schema.

        Returns:
            A SearchApplication instance.
        """
        # Access by field name for robustness, assuming schema matches
        return cls(engine_id=row["engine_id"], region=row["region"])

    def to_dict(self):
        """Converts the SearchApplication instance to a dictionary."""
        return {
            "engine_id": self.engine_id,
            "region": self.region,
        }

    def get_client_options(self) -> Optional[ClientOptions]:
        """Generates API client options based on the application's region.

        Returns:
            ClientOptions configured with the regional endpoint, or None if
            the region is 'global'.
        """
        return (
            ClientOptions(
                api_endpoint=f"{self.region}-discoveryengine.googleapis.com"
            )
            if self.region != "global"
            else None
        )

    def get_serving_config(self) -> str:
        """Constructs the full serving config path for the Discovery Engine API.

        Returns:
            The formatted serving config string.
        """
        serving_config = f"projects/{PROJECT_ID}/locations/{self.region}"
        serving_config += f"/collections/default_collection/engines/{self.engine_id}"
        serving_config += "/servingConfigs/default_config"
        return serving_config

class Engine(BaseModel):
    """Represents a discovered Discovery Engine instance."""
    name: str
    engine_id: str
    region: str


@dataclass
class SearchResult:
    """Represents a single document result from a search query."""
    document_id: str
    title: str
    snippet: str
    link: Optional[str] = None
    content: Optional[str] = None


@dataclass
class SearchResultsWithSummary:
    """Represents the complete results of a search, including a summary."""
    results: List[SearchResult]
    summary: Optional[str] = None
