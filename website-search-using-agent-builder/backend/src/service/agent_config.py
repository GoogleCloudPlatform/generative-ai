from src.model.http_status import BadRequest
from src.model.agent_config import AgentConfig
from src.repository.big_query import BIG_QUERY_DATASET, BigQueryRepository
from typing import List

AGENT_CONFIG_TABLE = "agent_config"
AGENT_CONFIG_TABLE_ID_COLUMN = "name"

class AgentConfigService:

    def __init__(self):
        self.repository = BigQueryRepository()
    
    def get_all(self) -> List[AgentConfig]:
        agent_configs = []
        results = self.repository.run_query(f"SELECT * FROM `{BIG_QUERY_DATASET}.{AGENT_CONFIG_TABLE}`")
        for row in results:
            agent_config = AgentConfig.__from_row__(row)
            agent_configs.append(agent_config)

        return agent_configs

    def create(self, agent_config: AgentConfig) -> AgentConfig:
        if self.get(agent_config.name):
            raise BadRequest(detail=f"AgentConfig with name {agent_config.name} already exists")
        self.repository.insert_row(AGENT_CONFIG_TABLE, agent_config.to_insert_string())
        return agent_config
    
    def update(self, name: str, agent_config: AgentConfig):
        update_dict = {
            'url': f'"{agent_config.url}"',
        }
        self.repository.update_row_by_id(AGENT_CONFIG_TABLE, AGENT_CONFIG_TABLE_ID_COLUMN, name, update_dict)

    def delete(self, name: str):
        self.repository.delete_row_by_id(AGENT_CONFIG_TABLE, AGENT_CONFIG_TABLE_ID_COLUMN, name)