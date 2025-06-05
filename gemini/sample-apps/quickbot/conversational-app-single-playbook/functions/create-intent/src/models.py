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