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

from fastapi import APIRouter, HTTPException
from src.model.http_status import BadRequest
from src.model.intent import CreateIntentRequest, Intent
from src.model.event import IntentCreateEvent
from src.repository.task import TaskRepository
from src.service.index_endpoint import IndexEndpointService
from src.service.intent import IntentService

router = APIRouter(
    prefix="/api/intents",
    tags=["intents"],
    responses={404: {"description": "Not found"}},
)


@router.get("")
async def get_intents():
    service = IntentService()
    intents = service.get_all()

    for intent in intents:
        if not intent.is_active():
            index_endpoint_service = IndexEndpointService()
            if index_endpoint_service.endpoint_has_deployed_indexes(
                intent.get_standard_name()
            ):
                intent.status = "5"
                service.update(intent.name, intent)

    return intents


@router.post("")
async def create_intent(intent: CreateIntentRequest):
    intent_service = IntentService()
    index_endpoint_service = IndexEndpointService()
    task_repository = TaskRepository()

    saved_intent = None
    index_endpoint = None
    try:
        saved_intent = intent_service.create(intent.to_intent())
        if intent.gcp_bucket:
            index_endpoint = index_endpoint_service.create_endpoint(
                saved_intent.get_standard_name()
            )
            task_repository.create(
                IntentCreateEvent(
                    intent_name=intent.name,
                    index_endpoint_resource=index_endpoint.resource_name,
                ),
            )
    except BadRequest as e:
        raise HTTPException(status_code=400, detail=e.detail)
    except Exception as e:
        print(e)
        if saved_intent:
            intent_service.delete(saved_intent.name)
        if index_endpoint:
            index_endpoint_service.delete_endpoint(index_endpoint)

    return saved_intent


@router.delete("/{intent_name}")
async def delete_intent(intent_name: str):
    service = IntentService()
    intent = service.get(intent_name)
    if intent.gcp_bucket:
        index_endpoint_service = IndexEndpointService()
        endpoint = index_endpoint_service.get_endpoint(
            intent.get_standard_name()
        )
        index_endpoint_service.delete_endpoint(endpoint)
    service.delete(intent_name)
    return


@router.put("/{intent_name}")
async def update_intent(intent_name: str, intent: Intent):
    service = IntentService()
    return service.update(intent_name, intent)
