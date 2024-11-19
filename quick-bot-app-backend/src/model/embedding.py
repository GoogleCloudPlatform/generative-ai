
from google.cloud.bigquery import SchemaField
from pydantic import BaseModel
from typing import List, Optional


class Embedding(BaseModel):
    id: str
    text: str
    index: str
    author: str
    timestamp: Optional[str] = None

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
    
    def to_insert_string(self):
        return f'"{self.id}", """{self.text}""", "{self.index}", "{self.author}", CURRENT_TIMESTAMP()'