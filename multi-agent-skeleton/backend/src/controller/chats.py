import json

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Response
from fastapi import WebSocket
from vertexai import agent_engines

from src.model.chats import Chat
from src.model.chats import CreateChatRequest
from src.service.chats import ChatsService
from src.service.intent import IntentService
from src.service.intent_matching import IntentMatchingService

DEFAULT_USER_ID = "traveler0115"

router = APIRouter(
    prefix="/api/chats",
    tags=["chats"],
    responses={404: {"description": "Not found"}},
)


@router.websocket("")
async def websocket_chat(
    *,
    websocket: WebSocket,
    background_tasks: BackgroundTasks,
):
    await websocket.accept()
    intent = get_default_intent()
    remote_agent_resource_id = intent.remote_agent_resource_id
    item_json = await websocket.receive_text()
    print(f"Received item: {item_json}")
    item = CreateChatRequest(**json.loads(item_json))

    remote_agent = agent_engines.get(remote_agent_resource_id)
    print(f"Trying remote agent: {remote_agent_resource_id}")
    if item.chat_id:
        session = remote_agent.get_session(
            user_id=DEFAULT_USER_ID, session_id=item.chat_id
        )
    else:
        session = remote_agent.create_session(user_id=DEFAULT_USER_ID)
    print(f'Trying remote agent with session: {session["id"]}')
    await websocket.send_json({"operation": "start"})

    try:
        while True:
            message = await websocket.receive_text()
            for (
                event
            ) in remote_agent.stream_query(  # TODO: Streaming should be enabled on the frontend
                user_id=DEFAULT_USER_ID,
                session_id=session["id"],
                message=message,
            ):
                content = event.get("content")
                if content:
                    for part in event["content"]["parts"]:
                        await websocket.send_json(part)
                        log_response(
                            background_tasks,
                            intent,
                            message,
                            json.dumps(part),
                            session,
                            [],
                        )

            else:
                await websocket.send_json({"operation": "close"})
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()


@router.post("")
async def chat(
    item: CreateChatRequest, response: Response, background_tasks: BackgroundTasks
):
    intent = get_default_intent()
    message = item.text
    remote_agent_resource_id = intent.remote_agent_resource_id

    remote_agent = agent_engines.get(remote_agent_resource_id)
    print(f"Trying remote agent: {remote_agent_resource_id}")
    session = None
    if item.chat_id:
        session = remote_agent.get_session(
            user_id=DEFAULT_USER_ID, session_id=item.chat_id
        )
    else:
        session = remote_agent.create_session(user_id=DEFAULT_USER_ID)
        print(f'Trying remote agent with session: {session["id"]}')

    answer = []
    for (
        event
    ) in remote_agent.stream_query(  # TODO: Streaming should be enabled on the frontend
        user_id=DEFAULT_USER_ID,
        session_id=session["id"],
        message=message,
    ):
        content = event.get("content")
        if content:
            for part in event["content"]["parts"]:
                if part.get("text"):
                    answer.append(
                        part["text"]
                    )  # TODO: Currently getting only text out, but the whole thinking and function calls process is available here

    model_response = " ".join(answer)

    # suggestedQuestion = intent_matching_service.get_suggested_questions(item.text, intent)
    suggested_questions = []

    final_response = log_response(
        background_tasks, intent, message, model_response, session, suggested_questions
    )

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return final_response


def log_response(
    background_tasks, intent, message, model_response, session, suggested_questions
):
    final_response = Chat(
        id=session["id"],
        question=message,
        answer=model_response,
        intent=intent.name,
        suggested_questions=suggested_questions,
    )
    background_tasks.add_task(
        ChatsService().insert_chat,
        final_response,
    )
    return final_response


def get_default_intent():
    intents = IntentService().get_all()
    intent_matching_service = IntentMatchingService(intents)
    intent = intent_matching_service.get_intent_from_query("")
    return intent
