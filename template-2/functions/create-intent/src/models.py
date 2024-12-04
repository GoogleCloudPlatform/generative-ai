from google.cloud.bigquery import SchemaField
from pydantic import BaseModel
from typing import List


class Intent(BaseModel):
    name: str
    ai_model: str
    ai_temperature: float
    prompt: str
    is_active: bool
    gcp_bucket: str = ""

    def __schema__() -> List[SchemaField]:
        return [
            SchemaField("name", "STRING", mode="REQUIRED"),
            SchemaField("ai_model", "STRING", mode="REQUIRED"),
            SchemaField("ai_temperature", "NUMBER", mode="REQUIRED"),
            SchemaField("prompt", "STRING", mode="REQUIRED"),
            SchemaField("is_active", "BOOLEAN", mode="REQUIRED"),
            SchemaField("gcp_bucket", "STRING", mode="REQUIRED"),
        ]
    
    def __from_row__(row):
        return Intent(
            name=row[0],
            ai_model=row[1],
            ai_temperature=row[2],
            prompt=row[3],
            is_active=row[4],
            gcp_bucket=row[5],
        )

    def to_dict(self):
        return {
            "name": self.name,
            "ai_model": self.ai_model,
            "ai_temperature": self.ai_temperature,
            "prompt": self.prompt,
            "is_active": self.is_active,
            "gcp_bucket": self.gcp_bucket,
        }
    
class Embedding(BaseModel):
    id: str
    text: str
    index: str
    author: str
    timestamp: str

    def __schema__() -> List[SchemaField]:
        return [
            SchemaField("id", "STRING", mode="REQUIRED"),
            SchemaField("text", "STRING", mode="REQUIRED"),
            SchemaField("index", "STRING", mode="REQUIRED"),
            SchemaField("author", "STRING", mode="REQUIRED"),
            SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        ]

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "index": self.index,
            "author": self.author,
            "timestamp": self.timestamp,
        }