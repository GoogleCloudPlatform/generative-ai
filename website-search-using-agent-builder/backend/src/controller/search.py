from fastapi import APIRouter
from src.model.search import CreateSearchRequest, ResponseModel, SearchApplication
from src.model.agent_config import AgentConfig
from src.service.agent_config import AgentConfigService

from src.service.search import SearchService

router = APIRouter(
    prefix="/api/search",
    tags=["searches"],
    responses={404: {"description": "Not found"}},
)

@router.post("")
async def search(item: CreateSearchRequest):
    service = AgentConfigService()
    agent_configs = service.get_all()
    agent_config = None
    if agent_configs:
        agent_config = agent_configs[0]  # Extract the first element
        print(f"Agent config: {agent_config}")
    else:
        print("agent_configs is empty.")
    
    service = SearchService(agent_config.url)
    return service.search(item.term)