from google.cloud.bigquery import SchemaField
from pydantic import BaseModel
from typing import List


class Intent(BaseModel):
    name: str
    ai_model: str
    ai_temperature: float
    prompt: str
    status: str
    gcp_bucket: str = ""
    questions: List[str]

    def __schema__() -> List[SchemaField]:
        return [
            SchemaField("name", "STRING", mode="REQUIRED"),
            SchemaField("ai_model", "STRING", mode="REQUIRED"),
            SchemaField("ai_temperature", "NUMERIC", mode="REQUIRED"),
            SchemaField("prompt", "STRING", mode="REQUIRED"),
            SchemaField("status", "STRING", mode="REQUIRED"),
            SchemaField("gcp_bucket", "STRING", mode="REQUIRED"),
            SchemaField("questions", "STRING", mode="REPEATED"),
        ]

    def __from_row__(row):
        return Intent(
            name=row[0],
            ai_model=row[1],
            ai_temperature=row[2],
            prompt=row[3],
            status=row[4],
            gcp_bucket=row[5],
            questions=row[6],
        )

    def to_dict(self):
        return {
            "name": self.name,
            "ai_model": self.ai_model,
            "prompt": self.prompt,
            "status": self.status,
            "gcp_bucket": self.gcp_bucket,
            "questions": self.questions,
        }

    def to_insert_string(self):
        return f'"{self.name}", "{self.ai_model}", {self.ai_temperature},"""{self.prompt}""", "{self.status}", "{self.gcp_bucket}", {str(self.questions)}'

    def is_active(self) -> bool:
        return self.status == "5"

    def get_standard_name(self) -> str:
        return self.name.lower().replace(" ", "-").replace("_", "-")


class CreateIntentRequest(BaseModel):
    name: str
    gcp_bucket: str = ""
    ai_model: str
    ai_temperature: float
    prompt: str
    questions: List[str]

    def to_dict(self):
        return {
            "name": self.name,
            "gcp_bucket": self.gcp_bucket,
            "ai_model": self.ai_model,
            "ai_temperature": self.ai_temperature,
            "prompt": self.prompt,
            "questions": self.questions,
        }

    def to_intent(self) -> Intent:
        return Intent(
            name=self.name,
            ai_model=self.ai_model,
            ai_temperature=self.ai_temperature,
            prompt=self.prompt,
            status="1",
            gcp_bucket=self.gcp_bucket,
            questions=self.questions,
        )
