"""Agent entry point for ADK web."""

import dotenv
import gemini_agent

dotenv.load_dotenv()

# ADK web looks for 'root_agent' in this file.
root_agent = gemini_agent.GeminiAgent()
