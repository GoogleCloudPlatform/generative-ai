"""Pydantic models for Intent and Embedding data structures."""
from typing import List
from google.cloud.bigquery import SchemaField
from pydantic import BaseModel


class Intent(BaseModel):
    """
    Represents an intent configuration stored in BigQuery.
    """

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
        """
        Factory method to create an Intent object from a BigQuery Row.

        Args:
            row: A google.cloud.bigquery.Row object.

        Returns:
            An Intent instance.
        """
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
        """
        Converts the Intent object to a dictionary suitable for BigQuery insertion.
        Handles datetime formatting.
        """
        return {
            "name": self.name,
            "ai_model": self.ai_model,
            "prompt": self.prompt,
            "status": self.status,
            "gcp_bucket": self.gcp_bucket,
            "questions": self.questions,
        }


class Embedding(BaseModel):
    """
    Represents a text chunk and its associated metadata to be stored in BigQuery.
    """

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
        """
        Converts the Embedding object to a dictionary suitable for BigQuery JSON insertion.
        """
        return {
            "id": self.id,
            "text": self.text,
            "index": self.index,
            "author": self.author,
            "timestamp": self.timestamp,
        }
