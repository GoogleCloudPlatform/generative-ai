from fastapi import APIRouter
from src.model.agent_config import AgentConfig
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
async def create_agent_config(agent_config: AgentConfig):
    service = AgentConfigService()
    return service.create(agent_config)

@router.delete("/{agent_config_name}")
async def delete_agent_config(agent_config_name: str):
    service = AgentConfigService()
    return service.delete(agent_config_name)

@router.put("/{agent_config_name}")
async def update_agent_config(agent_config_name: str, agent_config: AgentConfig):
    service = AgentConfigService()
    return service.update(agent_config_name, agent_config)