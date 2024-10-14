"""Node Re-ranker class for async execution"""

from collections.abc import Callable
import logging

import google.auth
import google.auth.transport.requests
from llama_index.core import QueryBundle, Settings
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from llama_index.core.indices.utils import (
    default_format_node_batch_fn,
    default_parse_choice_select_answer_fn,
)
from llama_index.core.llms.llm import LLM
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.prompts import BasePromptTemplate
from llama_index.core.prompts.default_prompts import DEFAULT_CHOICE_SELECT_PROMPT
from llama_index.core.prompts.mixin import PromptDictType
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.service_context import ServiceContext
from llama_index.core.settings import llm_from_settings_or_context
from llama_index.llms.vertex import Vertex
import requests

logging.basicConfig(level=logging.INFO)  # Set the desired logging level
logger = logging.getLogger(__name__)


# Initialize the LLM and set it in the Settings
llm = Vertex(model="gemini-1.5-flash", temperature=0.0)
Settings.llm = llm


def authenticate_google():
    """Authenticate using Google credentials and return the access token."""
    credentials, project_id = google.auth.default(
        quota_project_id="pr-sbx-vertex-genai"
    )
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    return credentials.token


def call_reranker(query, records, google_token):
    """Calls the reranker API with the given query and records.

    Args:
      query: The search query.
      records: A list of dictionaries, where each dictionary represents a record
        with "id", "title", and "content" fields.

    Returns:
      The API response as a dictionary.
    """
    # Replace 'your-project-id' with your actual Google Cloud project ID
    project_id = "pr-sbx-vertex-genai"
    model_name = "semantic-ranker-512@latest"
    url = f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/global/rankingConfigs/default_ranking_config:rank"

    headers = {
        "Authorization": "Bearer " + google_token,
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id,
    }

    data = {
        "model": model_name,
        "query": query,
        "records": records,
    }

    response = requests.post(url, headers=headers, json=data)
    print(response)
    response.raise_for_status()  # Raise an error if the request failed
    return response.json()


class GoogleReRankerSecretSauce(BaseNodePostprocessor):
    def _postprocess_nodes(
        self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None
    ) -> list[NodeWithScore]:
        google_token = authenticate_google()

        records = []
        for node_wscore in nodes:
            records.append(
                {
                    "id": node_wscore.node.id_,
                    "title": node_wscore.node.metadata["title"],
                    "content": node_wscore.node.text,
                }
            )
        response_json = call_reranker(query_bundle.query_str, records, google_token)

        records = response_json["records"]
        new_nodes_wscores = []
        for r in records:
            node = TextNode(id_=r["id"], text=r["content"])
            node_wscore = NodeWithScore(node=node, score=r["score"])
            new_nodes_wscores.append(node_wscore)

        return sorted(new_nodes_wscores, key=lambda x: x.score or 0.0, reverse=True)


class CustomLLMRerank(BaseNodePostprocessor):
    """LLM-based reranker."""

    top_n: int = Field(description="Top N nodes to return.")
    choice_select_prompt: BasePromptTemplate = Field(
        description="Choice select prompt."
    )
    choice_batch_size: int = Field(description="Batch size for choice select.")
    llm: LLM = Field(description="The LLM to rerank with.")

    _format_node_batch_fn: Callable = PrivateAttr()
    _parse_choice_select_answer_fn: Callable = PrivateAttr()

    def __init__(
        self,
        llm: LLM | None = None,
        choice_select_prompt: BasePromptTemplate | None = None,
        choice_batch_size: int = 10,
        format_node_batch_fn: Callable | None = None,
        parse_choice_select_answer_fn: Callable | None = None,
        service_context: ServiceContext | None = None,
        top_n: int = 10,
    ) -> None:
        choice_select_prompt = choice_select_prompt or DEFAULT_CHOICE_SELECT_PROMPT

        llm = llm or llm_from_settings_or_context(Settings, service_context)

        self._format_node_batch_fn = (
            format_node_batch_fn or default_format_node_batch_fn
        )
        self._parse_choice_select_answer_fn = (
            parse_choice_select_answer_fn or default_parse_choice_select_answer_fn
        )

        super().__init__(
            llm=llm,
            choice_select_prompt=choice_select_prompt,
            choice_batch_size=choice_batch_size,
            service_context=service_context,
            top_n=top_n,
        )

    def _get_prompts(self) -> PromptDictType:
        """Get prompts."""
        return {"choice_select_prompt": self.choice_select_prompt}

    def _update_prompts(self, prompts: PromptDictType) -> None:
        """Update prompts."""
        if "choice_select_prompt" in prompts:
            self.choice_select_prompt = prompts["choice_select_prompt"]

    @classmethod
    def class_name(cls) -> str:
        return "LLMRerank"

    async def postprocess_nodes(
        self,
        nodes: list[NodeWithScore],
        query_bundle: QueryBundle | None = None,
        query_str: str | None = None,
    ) -> list[NodeWithScore]:
        """Postprocess nodes."""
        if query_str is not None and query_bundle is not None:
            raise ValueError("Cannot specify both query_str and query_bundle")
        elif query_str is not None:
            query_bundle = QueryBundle(query_str)
        else:
            pass
        return await self._postprocess_nodes(nodes, query_bundle)

    async def _postprocess_nodes(
        self,
        nodes: list[NodeWithScore],
        query_bundle: QueryBundle | None = None,
    ) -> list[NodeWithScore]:
        if query_bundle is None:
            raise ValueError("Query bundle must be provided.")
        if len(nodes) == 0:
            return []

        initial_results: list[NodeWithScore] = []
        for idx in range(0, len(nodes), self.choice_batch_size):
            nodes_batch = [
                node.node for node in nodes[idx : idx + self.choice_batch_size]
            ]

            query_str = query_bundle.query_str
            fmt_batch_str = self._format_node_batch_fn(nodes_batch)
            # call each batch independently
            raw_response = await self.llm.apredict(
                self.choice_select_prompt,
                context_str=fmt_batch_str,
                query_str=query_str,
            )

            logging.info(raw_response)
            try:
                raw_choices, relevances = self._parse_choice_select_answer_fn(
                    raw_response, len(nodes_batch)
                )
            # Try again
            except IndexError:
                raw_response = await self.llm.apredict(
                    self.choice_select_prompt,
                    context_str=fmt_batch_str,
                    query_str=query_str,
                )
                raw_choices, relevances = self._parse_choice_select_answer_fn(
                    raw_response, len(nodes_batch)
                )
            choice_idxs = [int(choice) - 1 for choice in raw_choices]
            choice_nodes = [nodes_batch[idx] for idx in choice_idxs]
            relevances = relevances or [1.0 for _ in choice_nodes]
            initial_results.extend(
                [
                    NodeWithScore(node=node, score=relevance)
                    for node, relevance in zip(choice_nodes, relevances)
                ]
            )

        return sorted(initial_results, key=lambda x: x.score or 0.0, reverse=True)[
            : self.top_n
        ]
