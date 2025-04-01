# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""LangGraph agent for a semantic router."""

from concierge.agents.semantic_router.graph import FINAL_NODE, load_graph
from concierge.agents.semantic_router.schemas import AgentConfig

__all__ = ["load_graph", "FINAL_NODE", "AgentConfig"]
