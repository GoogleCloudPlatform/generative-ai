"""Provides a repository class for interacting with Google BigQuery."""
import logging
from typing import List
from google.cloud.bigquery import Client

from src.models import Embedding

BIG_QUERY_DATASET = ""

EMBEDDINGS_TABLE = "embeddings"
EMBEDDINGS_ID_COLUMN = "id"
EMBEDDINGS_TEXT_COLUMN = "text"
EMBEDDINGS_INDEX_COLUMN = "index"

INTENTS_TABLE = "intents"
INTENTS_TABLE_ID_COLUMN = "name"
INTENTS_TABLE_STATUS_COLUMN = "status"


class BigQueryRepository:
    """
    Provides an interface for interacting with Google BigQuery tables 
    related to intents and embeddings.
    """

    def __init__(self):
        """
        Initializes the BigQueryRepository.

        Args:
            project_id: The Google Cloud project ID. If None, 
            it attempts to infer from the environment.
            location: The location of the BigQuery dataset (e.g., 'US', 'EU').
        """
        self.client: Client = Client()

    def run_query(self, query: str):
        """
        Executes a BigQuery query and returns the results.

        Args:
            query: The SQL query string.
            job_config: Optional BigQuery JobConfig.

        Returns:
            A BigQuery RowIterator for the results.

        Raises:
            google.cloud.exceptions.GoogleCloudError: If the query fails.
        """
        logging.info(query)
        return self.client.query(query).result()

    def get_row_by_id(self, table_id: str, id_column: str, id: str):
        """
        Retrieves a row (or rows) from a BigQuery table based on a specific ID column value.

        Args:
            table_id: The fully qualified ID of the BigQuery table (e.g., 'project.dataset.table').
            id_column: The name of the column to filter by.
            row_id: The value to match in the id_column.

        Returns:
            A BigQuery RowIterator for the matching rows.
        """
        query = f"""
                SELECT * FROM `{BIG_QUERY_DATASET}.{table_id}` WHERE {id_column} = "{id}";
            """
        return self.run_query(query)

    def insert_rows(self, table_id: str, embeddings: List[Embedding]):
        """
        Inserts multiple rows into a specified BigQuery table.

        Args:
            table_id: The fully qualified ID of the BigQuery table (e.g., 'project.dataset.table').
            rows: A list of objects to insert. Each object should have attributes
                  corresponding to the table's columns, or be a dictionary.
                  Assumes objects have a `to_dict()` method if they are not dicts.
        """
        values = [embedding.to_dict() for embedding in embeddings]
        errors = self.client.insert_rows(
            f"{BIG_QUERY_DATASET}.{table_id}", values, Embedding.__schema__()
        )
        if not errors:
            print("Embeddings added")
        else:
            print(f"Encountered errors while inserting rows: {errors}")
            raise Exception("Error inserting embeddings in BQ")

    def update_intent_status(self, intent_name: str, intent_status: str):
        """
        Updates the status of a specific intent in the intents table.

        Assumes the intents table has columns named 'name' (or whatever INTENTS_TABLE_ID_COLUMN is)
        and 'status'.

        Args:
            intent_name: The name (ID) of the intent to update.
            status: The new status value to set.
        """
        query = f"""
            UPDATE `{BIG_QUERY_DATASET}.{INTENTS_TABLE}`
             SET {INTENTS_TABLE_STATUS_COLUMN} = "{intent_status}"
             WHERE {INTENTS_TABLE_ID_COLUMN} = "{intent_name}"
            """
        return self.run_query(query)
