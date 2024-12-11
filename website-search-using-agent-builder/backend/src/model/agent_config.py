from google.cloud.bigquery import SchemaField
from pydantic import BaseModel
from typing import List


class AgentConfig(BaseModel):
    name: str
    url: str

    def __schema__() -> List[SchemaField]:
        return [
            SchemaField("name", "STRING", mode="REQUIRED"),
            SchemaField("url", "STRING", mode="REQUIRED")
        ]
    
    def __from_row__(row):
        return AgentConfig(
            name=row[0],
            url=row[1]
        )

    def to_dict(self):
        return {
            "name": self.name,
            "url": self.url,
        }
    
    def to_insert_string(self):
        return f'"{self.name}", "{self.url}"'
    
    def get_standard_name(self) -> str:
        return self.name.lower().replace(" ", "-").replace("_", "-")

class CreateAgentConfigRequest(BaseModel):
    name: str
    url: str

    def __schema__() -> List[SchemaField]:
        return [
            SchemaField("name", "STRING", mode="REQUIRED"),
            SchemaField("url", "STRING", mode="REQUIRED"),
        ]

    def to_dict(self):
        return {
            "name": self.name,
            "url": self.url,
        }
    
    def to_agent_config(self) -> AgentConfig:
        return AgentConfig(
            name=self.name,
            url=self.url,
        )