"""Agent entry point for ADK web."""

from a2a_a2ui_sample import gemini_agent
import dotenv

dotenv.load_dotenv()

# ADK web looks for 'root_agent' in this file.
root_agent = gemini_agent.GeminiAgent()
