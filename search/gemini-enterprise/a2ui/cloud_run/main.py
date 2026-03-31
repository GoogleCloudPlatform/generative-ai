"""Main entry point for the A2A A2UI sample agent."""

import os

import dotenv
import uvicorn
from a2a.server import tasks
from a2a.server.apps.jsonrpc import starlette_app
from a2a.server.request_handlers import default_request_handler
from agent_executor import AdkAgentToA2AExecutor
from gemini_agent import GeminiAgent

dotenv.load_dotenv()

# The URL of your deployed Cloud Function.
# It's best to set this as an environment variable in your deployment.
AGENT_URL = os.environ.get("AGENT_URL", "http://127.0.0.1:8000")

# 1. Create the AgentCard, RequestHandler, and App at the global scope.
agent = GeminiAgent()
agent_card = agent.create_agent_card(AGENT_URL)

request_handler = default_request_handler.DefaultRequestHandler(
    agent_executor=AdkAgentToA2AExecutor(),
    task_store=tasks.InMemoryTaskStore(),
)

# 2. The Functions Framework will automatically look for this 'app' variable.
app = starlette_app.A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler,
).build()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
