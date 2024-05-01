# Reasoning Engine in Vertex AI

[Reasoning Engine](https://cloud.google.com/vertex-ai/generative-ai/docs/reasoning-engine/overview)
(LangChain on Vertex AI) is a managed service that helps you to build and deploy
an agent reasoning framework. It gives you the flexibility to choose how much
reasoning you want to delegate to the LLM and how much you want to handle with
customized code. You can define Python functions that get used as tools via
Gemini Function Calling.

Reasoning Engine integrates closely with the Python SDK for the Gemini model in
Vertex AI, and it can manage prompts, agents, and examples in a modular way.
Reasoning Engine is compatible with LangChain, LlamaIndex, or other Python
frameworks.

## Sample notebooks

Description | Sample Name
-- | --
Intro to Building and Deploying an Agent with Reasoning Engine in Vertex AI | [intro_reasoning_engine.ipynb](intro_reasoning_engine.ipynb)
Building and Deploying a Google Maps API Agent with Reasoning Engine | [tutorial_google_maps_agent.ipynb](tutorial_google_maps_agent.ipynb)
