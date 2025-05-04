"""Service layer for managing chatbot intents.

This module provides the IntentService class, which encapsulates the 
business logic for creating, retrieving, updating, and deleting intents. 
It interacts with BigQuery for persistent storage and Google Cloud Storage 
to validate data sources for certain intent types.
"""

from src.model.http_status import BadRequest
from src.model.intent import Intent
from src.repository.big_query import BIG_QUERY_DATASET, BigQueryRepository
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

    def get(self, intent_name: str):
        """Retrieves a single intent by its name.

        Args:
            intent_name: The unique name of the intent to retrieve.

        Returns:
            An Intent object if found, otherwise None.
        """
        intent = None
        results = self.repository.run_query(
            f'''SELECT * FROM `{BIG_QUERY_DATASET}.{INTENTS_TABLE}`
             WHERE name = "{intent_name}"'''
        )
        for row in results:
            intent = Intent.__from_row__(row)

        return intent

    def get_all(self) -> List[Intent]:
        """Retrieves all intents from the database.

        Returns:
            A list of Intent objects. Returns an empty list if no 
            intents are found.
        """
        intents = []
        results = self.repository.run_query(
            f"SELECT * FROM `{BIG_QUERY_DATASET}.{INTENTS_TABLE}`"
        )
        for row in results:
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
            raise BadRequest(
                detail=f"Intent with name {intent.name} already exists"
            )
        if intent.gcp_bucket and not self.gcs_repository.list(
            intent.gcp_bucket
        ):
            raise BadRequest(
                detail=f"No data found on {intent.gcp_bucket}, please, "
                "add your pdf files in the proper location."
            )
        if not intent.gcp_bucket:
            intent.status = "5"
        self.repository.insert_row(INTENTS_TABLE, intent.to_insert_string())
        return intent

    def update(self, intent_name: str, intent: Intent):
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
        update_dict = {
            "ai_model": f'"{intent.ai_model}"',
            "ai_temperature": f"{intent.ai_temperature}",
            "prompt": f'"""{intent.prompt}"""',
            "questions": f"{str(intent.questions)}",
            "status": f'"{intent.status}"',
        }
        self.repository.update_row_by_id(
            INTENTS_TABLE, INTENTS_TABLE_ID_COLUMN, intent_name, update_dict
        )

    def delete(self, intent_name: str):
        self.repository.delete_row_by_id(
            INTENTS_TABLE, INTENTS_TABLE_ID_COLUMN, intent_name
        )
