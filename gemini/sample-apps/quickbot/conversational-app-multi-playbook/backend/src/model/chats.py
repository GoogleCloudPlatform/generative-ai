# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

    @classmethod
    def __schema__(cls) -> List[SchemaField]:
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
