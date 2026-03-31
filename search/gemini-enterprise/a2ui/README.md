# A2UI on Gemini Enterprise

This folder contains examples and scripts to develop and use A2UI agents on Gemini Enterprise.

A2UI (Agent to UI) is a protocol that allows AI agents to dynamically construct and update user interfaces on the client side. By sending structured JSON payloads, agents can render rich UI components (cards, lists, forms, etc.) directly within the Gemini Enterprise interface. Refer o [A2UI](https://a2ui.org/) for more information.



## Folder Structure

This directory is organized into two sub-folders depending the deployment methods:

 - `cloud_run`: Contains scripts and configuration to deploy an agent to **Cloud Run**. This is suitable for building and deploying AI agents quickly, leveraging its speed and simplicity.
   - Starts with `cloud_run/README.md`.

 - `agent_engine`: Contains code to deploy to **Vertex AI Agent Engine**. Agent Engine provides additional features like agent context management, agent evaluation, agent lifecycle management, model-based conversation quality monitoring, and model tuning with context data.
   - Starts with `agent_engine/README.md`.

## Shared Resources

- `a2ui_schema.py`: Contains the JSON schema for A2UI messages, used for validation during development and at runtime.
- `a2ui_examples.py`: Provides several complete A2UI payload examples, such as Contact Cards and Action Confirmation modals.
- `agent_executor.py`: A base implementation of an A2A (Agent-to-Agent) executor that handles A2UI validation and response formatting.

## Registration in Gemini Enterprise

Regardless of the deployment method, agents must be registered with Gemini Enterprise. This involves:
1.  **Defining an A2A Agent Card**: Describing the agent's skills, name, and capabilities (including the **A2UI extension**).
2.  **Configuring Authorization**: Setting up OAuth2 or other authentication mechanisms to allow the agent to talk to secure services. This is optional for Cloud Run deployment but **mandatory for Agent Engine deployment**.
