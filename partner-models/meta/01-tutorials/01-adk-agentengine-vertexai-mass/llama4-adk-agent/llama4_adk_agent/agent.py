from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from .tools import (
    get_exchange_rate
)

root_agent = Agent(
    model=LiteLlm(model="vertex_ai/meta/llama-4-scout-17b-16e-instruct-maas"),  # Scout model
    # model=LiteLlm(model="vertex_ai/meta/llama-4-maverick-17b-128e-instruct-maas"), # Maverick model
    name='llama4_adk_agent',
    description='A helpful assistant for user questions including currency exchange rates',
    instruction='Answer user questions to the best of your knowledge. Use tools available to you if needed.',
    tools=[get_exchange_rate],
)