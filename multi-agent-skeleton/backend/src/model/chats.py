from google.cloud.bigquery import SchemaField
from pydantic import BaseModel
from typing import List, Optional


class Chat(BaseModel):
    id: str
    question: str
    answer: str
    intent: str
    suggested_questions: List[str]
    timestamp: Optional[str] = None

    def __schema__() -> List[SchemaField]:
        return [
            SchemaField("id", "STRING", mode="REQUIRED"),
            SchemaField("question", "STRING", mode="REQUIRED"),
            SchemaField("answer", "STRING", mode="REQUIRED"),
            SchemaField("intent", "STRING", mode="REQUIRED"),
            SchemaField("suggested_questions", "STRING", mode="REPEATED"),
            SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        ]

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "intent": self.intent,
            "suggested_questions": self.suggested_questions,
            "timestamp": self.timestamp,
        }

    def to_insert_string(self):
        return f'"{self.id}", """{self.question}""", """{self.answer}""", "{self.intent}", {str(self.suggested_questions)}, CURRENT_TIMESTAMP()'


class CreateChatRequest(BaseModel):
    text: str
    chat_id: Optional[str] = None
