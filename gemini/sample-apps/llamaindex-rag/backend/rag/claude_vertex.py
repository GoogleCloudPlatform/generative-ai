"""Llamaindex LLM implementation of Claude Vertex AI"""

from typing import Any

from anthropic import AnthropicVertex, AsyncAnthropicVertex
from llama_index.core.llms import (
    CompletionResponse,
    CompletionResponseGen,
    CustomLLM,
    LLMMetadata,
)
from llama_index.core.llms.callbacks import llm_completion_callback
from pydantic import Field, PrivateAttr


class ClaudeVertexLLM(CustomLLM):
    project_id: str = Field(description="The project ID for Vertex AI")
    region: str = Field(description="The region for Vertex AI")
    model_name: str = Field(description="The name of the Claude model to use")
    max_tokens: int = Field(
        description="The maximum number \
                            of tokens to generate"
    )
    system_prompt: str = Field(description="The system prompt to use")

    client: Any = PrivateAttr()
    async_client: Any = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self.client = AnthropicVertex(project_id=self.project_id, region=self.region)
        self.async_client = AsyncAnthropicVertex(
            project_id=self.project_id, region=self.region
        )

    @property
    def metadata(self) -> LLMMetadata:
        """Get LLM metadata."""
        return LLMMetadata(
            model_name=self.model_name,
            max_tokens=self.max_tokens,
            system_prompt=self.system_prompt,
        )

    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        message = self.client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        return CompletionResponse(text=message.content[0].text)

    @llm_completion_callback()
    async def acomplete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        message = await self.async_client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        return CompletionResponse(text=message.content[0].text)

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        with self.client.messages.stream(
            model=self.model_name,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            response = ""
            for text in stream.text_stream:
                response += text
                yield CompletionResponse(text=response, delta=text)
