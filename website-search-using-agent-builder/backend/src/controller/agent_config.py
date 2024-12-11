from uuid import uuid4
from fastapi import APIRouter, HTTPException
from src.model.http_status import BadRequest
from src.model.agent_config import CreateAgentConfigRequest, AgentConfig
from src.repository.big_query import BigQueryRepository
from src.service.agent_config import AgentConfigService

router = APIRouter(
    prefix="/api/agent-configs",
    tags=["agent-configs"],
    responses={404: {"description": "Not found"}},
)
@router.get("")
async def get_agent_configs():
    service = AgentConfigService()
    agent_configs = service.get_all()
    return agent_configs

@router.post("")
async def create_agent_config(agent_config: CreateAgentConfigRequest):
    agent_config_service = AgentConfigService()
    saved_agent_config = None
    try:
        saved_agent_config = agent_config_service.create(agent_config.to_agent_config())
    except BadRequest as e:
        raise HTTPException(status_code=400, detail=e.detail)
    except Exception as e:
        print(e)
        if saved_agent_config:
            agent_config_service.delete(saved_agent_config.name)
        
    return saved_agent_config

@router.delete("/{agent_config_name}")
async def delete_agent_config(agent_config_name: str):
    service = AgentConfigService()
    agent_config = service.get(agent_config_name)
    service.delete(agent_config)
    return

@router.put("/{agent_config_name}")
async def update_agent_config(agent_config_name: str, agent_config: AgentConfig):
    service = AgentConfigService()
    return service.update(agent_config_name, agent_config)