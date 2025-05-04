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
from typing import List


class Intent(BaseModel):
    name: str
    ai_model: str
    ai_temperature: float
    description: str
    prompt: str
    questions: List[str]
    is_active: bool
    gcp_bucket: str = ""

    def __schema__() -> List[SchemaField]:
        return [
            SchemaField("name", "STRING", mode="REQUIRED"),
            SchemaField("ai_model", "STRING", mode="REQUIRED"),
            SchemaField("ai_temperature", "NUMBER", mode="REQUIRED"),
            SchemaField("description", "STRING", mode="REQUIRED"),
            SchemaField("prompt", "STRING", mode="REQUIRED"),
            SchemaField("questions", "STRING", mode="REPEATED"),
            SchemaField("is_active", "BOOLEAN", mode="REQUIRED"),
            SchemaField("gcp_bucket", "STRING", mode="REQUIRED"),
        ]
    
    def __from_row__(row):
        return Intent(
            name=row[0],
            ai_model=row[1],
            ai_temperature=row[2],
            description=row[3],
            prompt=row[4],
            questions=row[5],
            is_active=row[6],
            gcp_bucket=row[7],
        )

    def to_dict(self):
        return {
            "name": self.name,
            "ai_model": self.ai_model,
            "ai_temperature": self.ai_temperature,
            "description": self.description,
            "prompt": self.prompt,
            "questions": self.questions,
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