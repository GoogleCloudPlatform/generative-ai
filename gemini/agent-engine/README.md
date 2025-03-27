# Agent Engine in Vertex AI

[Agent Engine](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview)
is a managed service that helps you to build and deploy agent reasoning
frameworks. It gives you the flexibility to choose how much reasoning you want
to delegate to the LLM and how much you want to handle with customized code. You
can define Python functions that get used as tools via Gemini Function Calling.

Agent Engine integrates closely with the Python SDK for the Gemini model in
Vertex AI, and it can manage prompts, agents, and examples in a modular way.
Agent Engine is compatible with LangChain, LlamaIndex, or other Python
frameworks.

## Sample notebooks

| Description                                                                          | Sample Name                                                                            |
| ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| Intro to Building and Deploying an Agent with Agent Engine in Vertex AI              | [intro_agent_engine.ipynb](intro_agent_engine.ipynb)                                   |
| Debugging and Optimizing Agents: A Guide to Tracing in Agent Engine                  | [tracing_agents_in_agent_engine.ipynb](tracing_agents_in_agent_engine.ipynb)           |
| Building a Conversational Search Agent with Agent Engine and RAG on Vertex AI Search | [tutorial_vertex_ai_search_rag_agent.ipynb](tutorial_vertex_ai_search_rag_agent.ipynb) |
| Building and Deploying a Google Maps API Agent with Agent Engine                     | [tutorial_google_maps_agent.ipynb](tutorial_google_maps_agent.ipynb)                   |
| Building and Deploying a LangGraph Application with Agent Engine in Vertex AI        | [tutorial_langgraph.ipynb](tutorial_langgraph.ipynb)                                   |
| Deploying a RAG Application with AlloyDB with Agent Engine                           | [tutorial_alloydb_rag_agent.ipynb](tutorial_alloydb_rag_agent.ipynb)                   |
| Deploying a RAG Application with Cloud SQL for PostgreSQL with Agent Engine          | [tutorial_cloud_sql_pg_rag_agent.ipynb](tutorial_cloud_sql_pg_rag_agent.ipynb)         |
