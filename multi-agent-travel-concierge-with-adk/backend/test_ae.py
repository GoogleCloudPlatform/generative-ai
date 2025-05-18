from vertexai import agent_engines
from vertexai.preview.reasoning_engines.templates.adk import AdkApp

from travel_concierge.agent import root_agent


message = "Plan for me a week-long trip to greece from poland for a family with 2 kids, aged 9 and 2. start date is May 4th 2025"
remote_agent_resource_id = (
    "projects/882302757206/locations/us-central1/reasoningEngines/6694680010923442176"
)

# [print(agent) for agent in agent_engines.list()]
remote_agent = agent_engines.get(remote_agent_resource_id)
# local_agent = root_agent
# remote_agent = AdkApp(agent=local_agent)
session = remote_agent.create_session(user_id="traveler0115")
print(f'Trying remote agent with session: {session["id"]}')
print(remote_agent.list_sessions(user_id="traveler0115"))

answer = []
for event in remote_agent.stream_query(
    user_id="traveler0115",
    session_id=session["id"],
    message=message,
):
    content = event.get("content")
    if content:
        for part in event["content"]["parts"]:
            if part.get("text"):
                answer.append(part["text"])

model_response = " ".join(answer)
print(f"model response is: {model_response}")
