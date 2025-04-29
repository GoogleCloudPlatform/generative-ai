from uuid import uuid4

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Response
from vertexai import agent_engines

from src.model.chats import Chat
from src.model.chats import CreateChatRequest
from src.service.chats import ChatsService
from src.service.intent import IntentService
from src.service.intent_matching import IntentMatchingService

router = APIRouter(
    prefix="/api/chats",
    tags=["chats"],
    responses={404: {"description": "Not found"}},
)


def send_message(resource_id: str, message: str) -> None:
    """Send a message to the deployed agent."""
    remote_agent = agent_engines.get(resource_id)
    session = remote_agent.create_session(
        user_id="traveler0115"
    )  # Optionally can provide initial states: state=initial_state
    print(f"Trying remote agent: {resource_id}")
    for event in remote_agent.stream_query(
        user_id="traveler0115",
        session_id=session["id"],
        message=message,
    ):
        print(event)
    print("Done.")


@router.post("")
async def chat(
    item: CreateChatRequest, response: Response, background_tasks: BackgroundTasks
):
    intents = IntentService().get_all()
    intent_matching_service = IntentMatchingService(intents)
    message = item.text

    intent = intent_matching_service.get_intent_from_query(item.text)
    remote_agent_resource_id = intent.remote_agent_resource_id

    remote_agent = agent_engines.get(remote_agent_resource_id)
    print(f"Trying remote agent: {remote_agent_resource_id}")
    session = remote_agent.create_session(user_id="traveler0115")
    print(f'Trying remote agent with session: {session["id"]}')

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

    # suggestedQuestion = intent_matching_service.get_suggested_questions(item.text, intent)

    # model_response = VertexAIService(intents).generate_text_from_model(
    #     item.text,
    #     intent,
    # )

    final_response = Chat(
        id=session["id"],
        question=message,
        answer=model_response,
        intent=intent.name,
        suggested_questions=[],
    )

    background_tasks.add_task(
        ChatsService().insert_chat,
        final_response,
    )

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return final_response
