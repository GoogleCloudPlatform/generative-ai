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
    item_json = await websocket.receive_json()
    print(f"Received item: {item_json}")
    item = CreateChatRequest(**item_json)

    remote_agent = agent_engines.get(remote_agent_resource_id)
    print(f"Trying remote agent: {remote_agent_resource_id}")
    session = remote_agent.create_session(user_id=DEFAULT_USER_ID)
    print(f'Trying remote agent with session: {session["id"]}')
    await websocket.send_json({"operation": "start"})

    try:
        while True:
            current_message_text: str

            if item:
                # Process the initial message (or a message carried over)
                current_message_text = item.text
                item = None  # CHG: Crucial - Consume/reset item after processing
                # This ensures the next loop iteration will wait for a new client message
            else:
                # Wait for a new message from the client
                # This block will be hit on the second and subsequent iterations
                # after the initial 'item' has been processed and set to None.
                print("Waiting for next client message...")
                try:
                    # CHG: Expecting subsequent messages to also be JSON with a 'text' field
                    next_item_json = await websocket.receive_json()
                    print(f"Received subsequent item: {next_item_json}")
                    # You might want to validate next_item_json structure here
                    if "text" not in next_item_json:
                        print(
                            "Warning: Subsequent message does not contain 'text' field. Closing."
                        )
                        await websocket.send_json(
                            {"error": "Invalid message format, 'text' field missing."}
                        )
                        await websocket.send_json({"operation": "closed"})
                        break  # Exit the loop
                    current_message_text = next_item_json["text"]
                except (
                    Exception
                ) as e:  # Catch potential WebSocketDisconnect or JSON errors
                    print(
                        f"Error receiving subsequent message or client disconnected: {e}"
                    )
                    break  # Exit the loop if client disconnects or sends bad data

            print(f"Processing message: {current_message_text}")
            for (
                event
            ) in remote_agent.stream_query(  # TODO: Streaming should be enabled on the frontend
                user_id=DEFAULT_USER_ID,
                session_id=session["id"],
                message=current_message_text,
            ):
                content = event.get("content")
                if content:
                    print(f"Got content: {content}")
                    for part in event["content"]["parts"]:
                        answer = {"answer": part}
                        await websocket.send_json(answer)
                        log_response(
                            background_tasks,
                            intent,
                            current_message_text,
                            json.dumps(answer),
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
            print(f"Got content: {content}")
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
