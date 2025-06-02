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

from google.cloud.bigquery import SchemaField, Row
from pydantic import BaseModel
from typing import List


class Intent(BaseModel):
    name: str
    ai_model: str
    ai_temperature: float
    description: str
    prompt: str
    questions: List[str]
    status: str
    gcp_bucket: str = ""

    @classmethod
    def __schema__(cls) -> List[SchemaField]:
        return [
            SchemaField("name", "STRING", mode="REQUIRED"),
            SchemaField("ai_model", "STRING", mode="REQUIRED"),
            SchemaField("ai_temperature", "NUMERIC", mode="REQUIRED"),
            SchemaField("description", "STRING", mode="REQUIRED"),
            SchemaField("prompt", "STRING", mode="REQUIRED"),
            SchemaField("questions", "STRING", mode="REPEATED"),
            SchemaField("status", "STRING", mode="REQUIRED"),
            SchemaField("gcp_bucket", "STRING", mode="REQUIRED"),
        ]

    @classmethod
    def __from_row__(cls, row: Row):
        return cls(
            name=row["name"],
            ai_model=row["ai_model"],
            ai_temperature=float(row["ai_temperature"]) if row["ai_temperature"] is not None else 0.0, # Ensure conversion from Decimal/Numeric
            description=row["description"],
            prompt=row["prompt"],
            questions=list(row["questions"]) if row["questions"] is not None else [], # Ensure it's a list
            status=row["status"],
            gcp_bucket=row["gcp_bucket"],
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
        }

    def to_insert_string(self):
        return f'"{self.name}", "{self.ai_model}", {self.ai_temperature},"{self.description}","""{self.prompt}""", {str(self.questions)}, "{self.status}", "{self.gcp_bucket}"'

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

    def to_dict(self):
        return {
            "name": self.name,
            "gcp_bucket": self.gcp_bucket,
            "ai_model": self.ai_model,
            "ai_temperature": self.ai_temperature,
            "description": self.description,
            "prompt": self.prompt,
            "questions": self.questions,
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
        )
