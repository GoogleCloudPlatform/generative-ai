# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from uuid import uuid4
from fastapi import APIRouter, BackgroundTasks, Response
from src.model.chats import CreateChatRequest, Chat
from src.service.intent import IntentService
from src.service.chats import ChatsService
from src.service.intent_matching import IntentMatchingService
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
    background_tasks: BackgroundTasks,
):
    intent_matching_service = IntentMatchingService()
    intents = IntentService().get_all()
    intent = intents[0]

    suggested_questions = intent_matching_service.get_suggested_questions(
        item.text, intent
    )

    model_response = VertexAIService(intents).generate_text_from_model(
        item.text,
        intent,
    )

    final_response = Chat(
        id=str(uuid4()),
        question=item.text,
        answer=model_response,
        intent=intent.name,
        suggested_questions=suggested_questions,
    )

    background_tasks.add_task(
        ChatsService().insert_chat,
        final_response,
    )

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return final_response
