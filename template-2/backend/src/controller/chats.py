from uuid import uuid4
from fastapi import APIRouter, BackgroundTasks, Response
from src.model.chats import CreateChatRequest, Chat
from src.service.intent import IntentService
from src.service.chats import ChatsService
from src.service.vertex_ai import VertexAIService

router = APIRouter(
    prefix="/api/chats",
    tags=["chats"],
    responses={404: {"description": "Not found"}},
)

@router.post("")
async def chat(
        item: CreateChatRequest,
        response: Response,
        background_tasks: BackgroundTasks
    ):
    intents = IntentService().get_all()
    intent = intents[0]
    
    model_response = VertexAIService(intents).generate_text_from_model(
        item.text,
        intent,
    )

    final_response = Chat(
        id=str(uuid4()),
        question=item.text,
        answer=model_response,
        intent=intent.name,
    )

    background_tasks.add_task(
        ChatsService().insert_chat,
        final_response,
    )

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return final_response