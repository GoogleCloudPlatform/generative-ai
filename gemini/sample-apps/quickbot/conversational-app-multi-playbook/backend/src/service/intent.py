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

"""Service layer for managing chatbot intents.

This module provides the IntentService class, which encapsulates the 
business logic for creating, retrieving, updating, and deleting intents. 
It interacts with BigQuery for persistent storage and Google Cloud Storage 
to validate data sources for certain intent types.
"""

from src.model.http_status import BadRequest
from src.model.intent import Intent
from src.repository.big_query import BigQueryRepository
from src.repository.cloud_storage import CloudStorageRepository
from typing import List

INTENTS_TABLE = "intents"
INTENTS_TABLE_ID_COLUMN = "name"


class IntentService:
    """Handles business logic related to chatbot intents.

    This service interacts with BigQuery and Cloud Storage repositories
    to manage intent data.

    Attributes:
        repository: An instance of BigQueryRepository for database operations.
        gcs_repository: An instance of CloudStorageRepository for GCS 
        operations.
    """

    def __init__(self):
        """Initializes the IntentService with necessary repositories."""
        self.repository = BigQueryRepository()
        self.gcs_repository = CloudStorageRepository()

    def get(self, intent_name: str) -> Intent | None:
        """Retrieves a single intent by its name.

        Args:
            intent_name: The unique name of the intent to retrieve.

        Returns:
            An Intent object if found, otherwise None.
        """
        intent = None
        # Use get_row_by_id for safer, parameterized query
        results = self.repository.get_row_by_id(
            table_id=INTENTS_TABLE,
            id_column=INTENTS_TABLE_ID_COLUMN,
            id_value=intent_name,
            id_value_type="STRING"
        )
        # get_row_by_id returns a RowIterator. Expect 0 or 1 row for a unique ID.
        row_list = list(results)
        if row_list:
            intent = Intent.__from_row__(row_list[0])
        return intent


    def get_all(self) -> List[Intent]:
        """Retrieves all intents from the database.

        Returns:
            A list of Intent objects. Returns an empty list if no 
            intents are found.
        """
        intents = []
        results = self.repository.get_all_rows(INTENTS_TABLE)
        for row in list(results):
            intent = Intent.__from_row__(row)
            intents.append(intent)
        return intents

    def create(self, intent: Intent) -> Intent:
        """Creates a new intent in the database.

        Validates that an intent with the same name doesn't already exist.
        If the intent uses a GCS bucket (`gcp_bucket` is set), it verifies
        that the bucket path contains data. Sets status to '5' ('Active'
        or 'Ready') if no GCS bucket is specified.

        Args:
            intent: The Intent object to create.

        Returns:
            The created Intent object.

        Raises:
            BadRequest: If an intent with the same name already exists, or if
                        a specified GCS bucket path is empty or invalid.
            google.cloud.exceptions.NotFound: If the GCS bucket specified 
            in the intent does not exist.
            google.api_core.exceptions.GoogleAPICallError: For other 
            GCS API errors.
        """
        if self.get(intent.name):
            raise BadRequest(detail=f"Intent with name {intent.name} already exists")
        if intent.gcp_bucket and not self.gcs_repository.list(intent.gcp_bucket):
            raise BadRequest(detail=f"No data found on {intent.gcp_bucket}, please, add your pdf files in the proper location.")
        if not intent.gcp_bucket:
            intent.status = "5" # Mark as active if no bucket (no indexing needed)

        intent_data = intent.to_dict()
        column_names = list(intent_data.keys())
        values_tuple = tuple(intent_data.values())

        # Call the updated insert_row method
        self.repository.insert_row(INTENTS_TABLE, column_names, values_tuple)
        return intent

    def update(self, intent_name: str, intent: Intent) -> None:
        """Updates an existing intent by its name.

        Constructs a dictionary of fields to update and passes it to the
        repository's update method.

        Args:
            intent_name: The name of the intent to update.
            intent: An Intent object containing the updated values. Note that
                    only specific fields (ai_model, ai_temperature, prompt,
                    questions, status) are currently updated by this method.

        Returns:
            None
        """
        # These are the fields intended to be updatable based on the previous implementation.
        # Ensure that the 'intent' Pydantic model instance (`intent`) provides these attributes.
        column_values_to_update = {
            'ai_model': intent.ai_model,
            'ai_temperature': intent.ai_temperature,
            'prompt': intent.prompt,
            'questions': intent.questions,
            'status': intent.status,
            'gcp_bucket': intent.gcp_bucket,
        }

        self.repository.update_row_by_id(
            table_id=INTENTS_TABLE,
            id_column=INTENTS_TABLE_ID_COLUMN,
            id_value=intent_name,
            column_values=column_values_to_update
        )

    def delete(self, intent_name: str):
        self.repository.delete_row_by_id(
            table_id=INTENTS_TABLE,
            id_column=INTENTS_TABLE_ID_COLUMN,
            id_value=intent_name,
            id_value_type="STRING"
        )
