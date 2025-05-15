from typing import List

from google.cloud.bigquery import SchemaField
from pydantic import BaseModel


class Intent(BaseModel):
    name: str
    ai_model: str
    ai_temperature: float
    description: str
    prompt: str
    questions: List[str]
    status: str
    gcp_bucket: str = ""
    remote_agent_resource_id: str

    def __schema__() -> List[SchemaField]:
        return [
            SchemaField("name", "STRING", mode="REQUIRED"),
            SchemaField("ai_model", "STRING", mode="REQUIRED"),
            SchemaField("ai_temperature", "NUMERIC", mode="REQUIRED"),
            SchemaField("description", "STRING", mode="REQUIRED"),
            SchemaField("prompt", "STRING", mode="REQUIRED"),
            SchemaField("questions", "STRING", mode="REPEATED"),
            SchemaField("status", "STRING", mode="REQUIRED"),
            SchemaField("gcp_bucket", "STRING", mode="REQUIRED"),
            SchemaField("remote_agent_resource_id", "STRING"),
        ]

    def __from_row__(row):
        return Intent(
            name=row[0],
            ai_model=row[1],
            ai_temperature=row[2],
            description=row[3],
            prompt=row[4],
            questions=row[5],
            status=row[6],
            gcp_bucket=row[7],
            remote_agent_resource_id=row[8],
        )

    def to_dict(self):
        return {
            "name": self.name,
            "ai_model": self.ai_model,
            "description": self.description,
            "prompt": self.prompt,
            "questions": self.questions,
            "status": self.status,
            "gcp_bucket": self.gcp_bucket,
            "remote_agent_resource_id": self.remote_agent_resource_id,
        }

    def to_insert_string(self):
        return f'"{self.name}", "{self.ai_model}", {self.ai_temperature},"{self.description}","""{self.prompt}""", {str(self.questions)}, "{self.status}", "{self.gcp_bucket}", "{self.remote_agent_resource_id}"'

    def is_active(self) -> bool:
        return self.status == "5"

    def get_standard_name(self) -> str:
        return self.name.lower().replace(" ", "-").replace("_", "-")


class CreateIntentRequest(BaseModel):
    name: str
    gcp_bucket: str = ""
    ai_model: str
    ai_temperature: float
    description: str
    prompt: str
    questions: List[str]
    remote_agent_resource_id: str

    def to_dict(self):
        return {
            "name": self.name,
            "gcp_bucket": self.gcp_bucket,
            "ai_model": self.ai_model,
            "ai_temperature": self.ai_temperature,
            "description": self.description,
            "prompt": self.prompt,
            "questions": self.questions,
            "remote_agent_resource_id": self.remote_agent_resource_id,
        }

    def to_intent(self) -> Intent:
        return Intent(
            name=self.name,
            ai_model=self.ai_model,
            ai_temperature=self.ai_temperature,
            description=self.description,
            prompt=self.prompt,
            questions=self.questions,
            status="1",
            gcp_bucket=self.gcp_bucket,
            remote_agent_resource_id=self.remote_agent_resource_id,
        )
