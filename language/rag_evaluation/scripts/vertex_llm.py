# Copyright 2024 Google LLC
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
"""Custom Class implementation"""

# Base LLM for Deepeval
from deepeval.models.base_model import DeepEvalBaseLLM

# Langchain package for Vertex AI
from langchain_google_vertexai import (  # type: ignore[import-untyped]
    ChatVertexAI,
    HarmBlockThreshold,
    HarmCategory,
)


class GoogleVertexAIDeepEval(DeepEvalBaseLLM):
    """Class to implement Vertex AI for DeepEval"""

    def __init__(self, model) -> None:  # pylint: disable=W0231
        """INitialise the model"""
        self.model = model

    def load_model(self) -> ChatVertexAI:  # pylint: disable=W0221
        return self.model

    def generate(self, prompt: str) -> str:  # pylint: disable=W0221
        chat_model = self.load_model()
        return chat_model.invoke(prompt).content

    async def a_generate(self, prompt: str) -> str:  # pylint: disable=W0221
        chat_model = self.load_model()
        res = await chat_model.ainvoke(prompt)
        return res.content

    def get_model_name(self) -> str:  # pylint: disable=W0236 , W0221
        return "Vertex AI Model"


# TODO(developer): Update the below lines
PROJECT_ID = "<your_project"
LOCATION = "your_region"

PROJECT_ID = "vertexai-pgt"
LOCATION = "us-central1"

# Initilialize safety filters for vertex model
safety_settings = {
    HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}

# Initialise the ChatVertexAI model
custom_model_gemini = ChatVertexAI(
    model_name="gemini-1.0-pro-002",
    safety_settings=safety_settings,
    project=PROJECT_ID,
    location=LOCATION,
    response_validation=False,  # Important since deepval cannot handle validation errors
)

# initiatialize the Deepeval wrapper class
google_vertexai_gemini_deepeval = GoogleVertexAIDeepEval(model=custom_model_gemini)
