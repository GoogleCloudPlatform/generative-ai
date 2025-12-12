# Copyright 2025 Google LLC
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


import os
from typing import Dict, Literal, Type

import google.auth
from google.auth.credentials import Credentials
from google.genai import types
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

# SERVICE_ACCOUNT_PATH logic removed. We rely on ADC.


class APISettings(BaseModel):
    host: str = Field(...)
    key: str = Field(..., repr=False)


class GoogleCloudSettings(BaseModel):
    """Settings for Google Cloud Platform resources."""

    project_id: str | None = Field(default=None, description="GCP Project ID")
    location: str = Field(default="us-central1", description="GCP Region")
    firestore_db_name: str = Field(default="financial-advisor", description="Firestore Database Name")
    use_vertex_ai: bool = Field(default=True, description="Whether to use Vertex AI or AI Studio")
    staging_bucket: str | None = Field(default=None, description="GCS Bucket for staging artifacts")
    docs_bucket_name: str | None = Field(default=None, description="GCS Bucket for RAG documents")
    http_options: types.HttpOptions = Field(default_factory=types.HttpOptions)

    @model_validator(mode="after")
    def resolve_project_details(self) -> "GoogleCloudSettings":
        """Attempts to resolve the Project ID from ADC if not explicitly set, and sets default bucket names."""
        if not self.project_id:
            try:
                _, resolved_project_id = google.auth.default()
                self.project_id = resolved_project_id
            except Exception:
                # If ADC fails (e.g. no creds), we leave it as None and let the app fail later
                # or handle it gracefully depending on usage.
                pass

        if self.project_id:
            if not self.docs_bucket_name:
                self.docs_bucket_name = f"{self.project_id}-financial-advisor-docs"

        return self


class VoiceSettings(BaseModel):
    """Settings for the Gemini Live (Audio/Voice) API."""

    model_id: str = Field(
        default="gemini-live-2.5-flash-preview-native-audio-09-2025",
        description="The Gemini model ID to use for voice/audio interactions.",
    )
    voice_name: str = Field(default="Puck", description="Name of the voice to use (e.g., Puck, Charon, Zephyr)")
    enable_affective_dialog: bool = Field(default=True)
    proactivity: bool = Field(default=True)
    response_modalities: list[str] = Field(default=["AUDIO"])


class AgentSettings(BaseModel):
    """Settings for the Text-based Agent (Tools, RAG, Chat)."""

    app_name: str = "Financial Advisor Application"
    default_user_id: str = "generic_authorized_user"
    mime_type: str = "audio/pcm;rate=16000"
    chat_model: str = Field(
        default="gemini-2.5-flash", description="The Gemini model ID to use for text-based chat and tool use."
    )


class VaisDatastoreSettings(BaseModel):
    display_name: str = "financial-advisor-datastore"
    id: str | None = None
    collection_id: str = "default_collection"
    content_config: str = "CONTENT_REQUIRED"
    solution_type: str = "SOLUTION_TYPE_SEARCH"
    industry_vertical: str = "GENERIC"
    location: str = "global"
    branch: str = "default_branch"


class VaisEngineSettings(BaseModel):
    """Settings for using VAiS as a Search Engine."""

    display_name: str = "financial-advisor-engine"
    id: str | None = None
    collection_id: str = "default_collection"
    location: str = "global"
    search_engine_config: dict = {
        "search_tier": "SEARCH_TIER_ENTERPRISE",
    }
    solution_type: str = "SOLUTION_TYPE_SEARCH"
    common_config: Dict[str, str] = {"companyName": "Financial Institution"}
    industry_vertical: str = "GENERIC"
    app_type: str = "APP_TYPE_INTRANET"
    knowledge_graph_config: Dict[str, bool] = {"enablePrivateKnowledgeGraph": True}


class SearchSettings(BaseModel):
    """Settings for using VAiS as a RAG Backend."""

    datastore_settings: VaisDatastoreSettings = VaisDatastoreSettings()
    engine_settings: VaisEngineSettings = VaisEngineSettings()
    alternative_region: str = "us-west1"
    display_name: str = "financial-advisor-corpus"
    description: str = "Leverage Vertex AI Search as the retrieval backend for RAG applications."
    rag_corpora_id: str = Field(
        default="SETUP_REQUIRED_RUN_TASK_INFRA_SETUP",
        description="The resource name of the RAG Corpus. Automatically set by 'task infra:setup'.",
    )

    @field_validator("rag_corpora_id")
    @classmethod
    def validate_corpus_id(cls, v: str) -> str:
        if v == "SETUP_REQUIRED_RUN_TASK_INFRA_SETUP":
            # We log a warning instead of raising an error to allow the app to start in 'stub' mode if needed,
            # but ideally this should be a ValueError in strict production.
            print("WARNING: RAG Corpus ID is not set. Please run 'task infra:setup' to generate it.")
        return v

    def get_resource_name(self, project_id: str) -> str:
        """Returns the full resource name for the RAG corpus."""
        if self.rag_corpora_id.startswith("projects/"):
            return self.rag_corpora_id
        return f"projects/{project_id}/locations/{self.alternative_region}/ragCorpora/{self.rag_corpora_id}"


class ApplicationSettings(BaseSettings):
    # Branding
    bank_name: str = "Financial Institution"
    advisor_name: str = "Advisor"

    # Functional Groups
    google_cloud: GoogleCloudSettings = Field(default_factory=GoogleCloudSettings, alias="vertex_ai")
    agent: AgentSettings = Field(default_factory=AgentSettings, alias="adk")
    voice: VoiceSettings = Field(default_factory=VoiceSettings, alias="gemini_live")
    search: SearchSettings = Field(default_factory=SearchSettings, alias="vais_rag_settings")

    # Infrastructure
    redis_url: str | None = Field(default=None, description="Redis URL for session persistence")
    backend_service_url: str = Field(
        default="http://localhost:8080",
        description="The base URL of the backend service, used for self-referential API calls (e.g. tools).",
    )

    # Runtime Environment Checks
    is_cloud_run: bool = Field(default_factory=lambda: bool(os.environ.get("K_SERVICE")))
    is_local_dev: bool = Field(default_factory=lambda: bool(os.environ.get("RUN_CONTAINER_LOCALLY")))

    log_level: Literal["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    use_json_logging: bool = True
    debug_logging: bool = False
    model_config = SettingsConfigDict(
        env_nested_delimiter="__", env_file=("taskfile.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Use ADC by default
        creds, project_id = google.auth.default()

        # Try to load from Secret Manager if possible, but don't crash if it fails
        try:
            from ..gcp_pydantic_settings import GoogleSecretManagerSettingsSource

            google_secret_manager_settings = GoogleSecretManagerSettingsSource(
                settings_cls, credentials=creds if isinstance(creds, Credentials) else None, project_id=project_id
            )
            return (
                init_settings,
                env_settings,
                dotenv_settings,
                file_secret_settings,
                google_secret_manager_settings,
            )
        except ImportError:
            return (
                init_settings,
                env_settings,
                dotenv_settings,
                file_secret_settings,
            )
        except Exception:
            # Fallback if Secret Manager access fails (common in local devs without permissions)
            return (
                init_settings,
                env_settings,
                dotenv_settings,
                file_secret_settings,
            )


if __name__ == "__main__":
    import pprint

    app_settings = ApplicationSettings()
    print("Settings Loaded")
    pprint.pprint(app_settings)
