# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from typing import Dict

from app.templates import FORMAT_DOCS, SYSTEM_INSTRUCTION
from app.vector_store import get_vector_store
import google
from google import genai
from google.genai.types import Content, FunctionDeclaration, LiveConnectConfig, Tool
from langchain_google_vertexai import VertexAIEmbeddings
import vertexai

# Constants
VERTEXAI = os.getenv("VERTEXAI", "true").lower() == "true"
LOCATION = "us-central1"
EMBEDDING_MODEL = "text-embedding-004"
MODEL_ID = "gemini-2.0-flash-exp"
URLS = [
    "https://cloud.google.com/architecture/deploy-operate-generative-ai-applications"
]

# Initialize Google Cloud clients
credentials, project_id = google.auth.default()
vertexai.init(project=project_id, location=LOCATION)


if VERTEXAI:
    genai_client = genai.Client(project=project_id, location=LOCATION, vertexai=True)
else:
    # API key should be set using GOOGLE_API_KEY environment variable
    genai_client = genai.Client(http_options={"api_version": "v1alpha"})

# Initialize vector store and retriever
embedding = VertexAIEmbeddings(model_name=EMBEDDING_MODEL)
vector_store = get_vector_store(embedding=embedding, urls=URLS)
retriever = vector_store.as_retriever()


def retrieve_docs(query: str) -> Dict[str, str]:
    """
    Retrieves pre-formatted documents about MLOps (Machine Learning Operations),
      Gen AI lifecycle, and production deployment best practices.

    Args:
        query: Search query string related to MLOps, Gen AI, or production deployment.

    Returns:
        A set of relevant, pre-formatted documents.
    """
    docs = retriever.invoke(query)
    formatted_docs = FORMAT_DOCS.format(docs=docs)
    return {"output": formatted_docs}


# Configure tools and live connection
retrieve_docs_tool = Tool(
    function_declarations=[
        FunctionDeclaration.from_function(client=genai_client, func=retrieve_docs)
    ]
)

tool_functions = {"retrieve_docs": retrieve_docs}

live_connect_config = LiveConnectConfig(
    response_modalities=["AUDIO"],
    tools=[retrieve_docs_tool],
    system_instruction=Content(parts=[{"text": SYSTEM_INSTRUCTION}]),
)
