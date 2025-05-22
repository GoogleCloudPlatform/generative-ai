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

"""
Provides a repository class for interacting with Google BigQuery.

This module defines the `BigQueryRepository` class, which encapsulates
common BigQuery operations like running queries, fetching rows by ID,
inserting, updating, and deleting rows. It relies on the 'BIG_QUERY_DATASET'
environment variable to target the correct dataset.
"""

from os import getenv
from typing import Dict, List
from google.cloud.bigquery import Client

BIG_QUERY_DATASET = getenv("BIG_QUERY_DATASET")


class BigQueryRepository:
    """
    A repository class for simplifying interactions with Google BigQuery.

    Provides methods for common CRUD (Create, Read, Update, Delete) operations
    on BigQuery tables within the configured dataset.
    """

    def __init__(self):
        """Initializes the BigQuery client."""
        self.client: Client = Client()

    def run_query(self, query: str):
        """
        Executes a BigQuery SQL query and returns the results.

        Args:
            query: The SQL query string to execute.
            **query_params: Optional parameters for parameterized queries
                           (recommended for security).

        Returns:
            A RowIterator object to iterate over the query results.

        Raises:
            google.cloud.exceptions.GoogleCloudError: If the query fails.
        """
        return self.client.query(query).result()

    def get_row_by_id(self, table_id: str, id_column: str, id_value: str):
        """
        Retrieves a single row from a table based on its ID.

        Args:
            table_id: The ID of the table (without dataset prefix).
            id_column: The name of the column containing the ID.
            id_value: The specific ID value to search for.

        Returns:
            A RowIterator containing the matching row(s) (usually one).
        """
        query = f"""
                SELECT * FROM `{BIG_QUERY_DATASET}.{table_id}`
                 WHERE {id_column} = "{id_value}";
            """
        return self.run_query(query)

    def insert_row(self, table_id: str, values: str):
        """
        Inserts a new row into the specified table.

        Args:
            table_id: The ID of the table.
            values: A string representing the values to insert, formatted
                    correctly for the SQL VALUES clause
                    (e.g., "'val1', 123, TRUE"). Consider using
                    parameterization or the insert_rows_json method
                    for safer and more structured inserts.

        Returns:
            The result of the query execution (often None for INSERT).
        """
        query = f"""
                INSERT INTO `{BIG_QUERY_DATASET}.{table_id}`
                 VALUES({values});
            """
        return self.run_query(query)

    def delete_multiple_rows_by_id(
        self, table_id: str, id_column: str, ids: List[str]
    ):
        """
        Deletes multiple rows from a table based on a list of IDs.

        Args:
            table_id: The ID of the table.
            id_column: The name of the column containing the IDs.
            ids: A list of ID values to delete.

        Returns:
            The result of the query execution.
        """
        return self.run_query(
            f"""
                DELETE FROM `{BIG_QUERY_DATASET}.{table_id}`
                 WHERE {id_column}
                 IN UNNEST([{', '.join(f'"{id}"' for id in ids)}]);
            """
        )

    def update_row_by_id(
        self,
        table_id: str,
        id_column: str,
        id_value: str,
        column_value: Dict[str, str],
    ):
        """
        Updates specific columns of a row identified by its ID.

        Args:
            table_id: The ID of the table.
            id_column: The name of the column containing the ID.
            id_value: The specific ID value of the row to update.
            column_value_map: A dictionary where keys are column names and
                              values are the new values (as strings, including
                              quotes if necessary for SQL).

        Returns:
            The result of the query execution.
        """
        sets = ""
        for k, v in column_value.items():
            sets += f"{k}={v},"
        sets = sets[:-1]
        query = f"""
                UPDATE `{BIG_QUERY_DATASET}.{table_id}`
                 SET {sets}
                 WHERE {id_column} = "{id_value}";
            """
        return self.run_query(query)

    def get_all_rows(self, table_id: str):
        """
        Retrieves all rows from the specified table.

        Args:
            table_id: The ID of the table.

        Returns:
            A RowIterator containing all rows in the table.
        """
        query = f"""
                    SELECT * from `{BIG_QUERY_DATASET}.{table_id}`
                """
        return self.run_query(query)

    def delete_row_by_id(self, table_id: str, id_column: str, id_value: str):
        """
        Deletes a single row from a table based on its ID.

        Args:
            table_id: The ID of the table.
            id_column: The name of the column containing the ID.
            id_value: The specific ID value of the row to delete.

        Returns:
            The result of the query execution.
        """
        query = f"""
                DELETE FROM `{BIG_QUERY_DATASET}.{table_id}`
                 WHERE {id_column} = "{id_value}"
            """
        return self.run_query(query)
