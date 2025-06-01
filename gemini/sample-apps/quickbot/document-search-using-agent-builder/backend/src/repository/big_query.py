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

import datetime
from decimal import Decimal
from os import getenv
from typing import Dict, List, Any, Optional, Tuple
from google.cloud.bigquery import (
    Client,
    QueryJobConfig,
    ScalarQueryParameter,
    ArrayQueryParameter,
    TableReference,
    DatasetReference
)
from google.cloud.bigquery.table import RowIterator
from google.cloud.exceptions import GoogleCloudError

_BIG_QUERY_DATASET_ENV = getenv("BIG_QUERY_DATASET")
if not _BIG_QUERY_DATASET_ENV:
    raise ValueError(
        "The BIG_QUERY_DATASET environment variable is not set. "
        "This is required for the BigQueryRepository to function."
    )
BIG_QUERY_DATASET: str = _BIG_QUERY_DATASET_ENV


class BigQueryRepository:
    """
    A repository class for simplifying interactions with Google BigQuery,
    using parameterized queries to prevent SQL injection.
    """

    def __init__(self):
        """Initializes the BigQuery client and project ID."""
        self.client: Client = Client()
        self.project_id: str = self.client.project
        self.dataset_id: str = BIG_QUERY_DATASET

    def _get_table_ref(self, table_id: str) -> TableReference:
        """Helper to get a TableReference object."""
        dataset_ref = DatasetReference(self.project_id, self.dataset_id)
        return TableReference(dataset_ref, table_id)

    def _validate_column_name(self, column_name: str):
        """Basic validation for column names."""
        if not column_name.replace("_", "").isalnum():
            raise ValueError(f"Invalid column name: {column_name}")
        
    def _create_scalar_query_parameter(self, name: str, value: Any) -> ScalarQueryParameter:
        """
        Creates a ScalarQueryParameter by inferring the BigQuery type from the value.
        """
        if isinstance(value, bool):
            return ScalarQueryParameter(name, "BOOL", value)
        if isinstance(value, int):
            return ScalarQueryParameter(name, "INT64", value)
        if isinstance(value, float):
            return ScalarQueryParameter(name, "FLOAT64", value)
        if isinstance(value, str):
            return ScalarQueryParameter(name, "STRING", value)
        if isinstance(value, datetime.datetime):
            return ScalarQueryParameter(name, "TIMESTAMP", value)
        if isinstance(value, datetime.date):
            return ScalarQueryParameter(name, "DATE", value)
        if isinstance(value, Decimal):
            return ScalarQueryParameter(name, "NUMERIC", value)
        if value is None:
            # For None, the type of the column in BQ will ultimately determine how NULL is handled.
            # Using STRING type for the parameter is a common safe default.
            return ScalarQueryParameter(name, "STRING", None) # Default to STRING for None
        
        # Fallback: attempt to convert other types to string.
        try:
            str_value = str(value)
            return ScalarQueryParameter(name, "STRING", str_value)
        except Exception as e:
            raise TypeError(
                f"Value for param '{name}' of type {type(value)} "
                f"could not be converted to a supported BigQuery scalar type: {e}"
            )

    def run_query(self, query: str, job_config: Optional[QueryJobConfig] = None) -> RowIterator:
        """
        Executes a BigQuery SQL query and returns the results.

        Args:
            query: The SQL query string to execute.
            job_config: Optional QueryJobConfig for parameterized queries.

        Returns:
            A RowIterator object to iterate over the query results.

        Raises:
            google.cloud.exceptions.GoogleCloudError: If the query fails.
        """
        try:
            query_job = self.client.query(query, job_config=job_config)
            return query_job.result()
        except GoogleCloudError as e:
            print(f"BigQuery Error: {e}")
            print(f"Query: {query}")
            if job_config and job_config.query_parameters:
                print(f"Parameters: {job_config.query_parameters}")
            raise

    def get_row_by_id(self, table_id: str, id_column: str, id_value: Any, id_value_type: str = "STRING") -> RowIterator:
        """
        Retrieves a single row from a table based on its ID using parameterized query.

        Args:
            table_id: The ID of the table (without dataset prefix).
            id_column: The name of the column containing the ID.
            id_value: The specific ID value to search for.
            id_value_type: The BigQuery type of the ID value (e.g., "STRING", "INT64").

        Returns:
            A RowIterator containing the matching row(s).
        """
        self._validate_column_name(id_column)
        query = f"""
            SELECT * FROM `{self.project_id}.{self.dataset_id}.{table_id}`
             WHERE `{id_column}` = @id_value;
        """
        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("id_value", id_value_type, id_value)
            ]
        )
        return self.run_query(query, job_config=job_config)

    def insert_rows_json(self, table_id: str, rows: List[Dict[str, Any]]) -> List[Dict]:
        """
        Inserts multiple rows into the specified table using JSON.
        This is the recommended method for insertions due to its safety and efficiency.

        Args:
            table_id: The ID of the table.
            rows: A list of dictionaries, where each dictionary represents a row
                  (column names as keys, values as row data).

        Returns:
            A list of error dictionaries if any rows failed to insert,
            otherwise an empty list.
        """
        table_ref = self._get_table_ref(table_id)
        errors_from_client = self.client.insert_rows_json(table_ref, rows)
        errors_list: List[Dict[str, Any]] = list(errors_from_client) # type: ignore
        if errors_list:
            print(f"Errors inserting rows into {table_id}: {errors_list}")
        return errors_list

    def insert_row(self, table_id: str, column_names: List[str], values: Tuple[Any, ...]) -> None:
        """
        Inserts a new row into the specified table using a parameterized query.
        Prefer `insert_rows_json` for multiple rows or complex data.

        Args:
            table_id: The ID of the table.
            column_names: A list of column names for the insert.
            values: A tuple of values corresponding to the column_names.

        Raises:
            ValueError: If column names are invalid or counts don't match.
            TypeError: If a value in `values` cannot be mapped to a BigQuery scalar type.
        """
        if not column_names or not values:
            raise ValueError("Column names and values cannot be empty.")
        if len(column_names) != len(values):
            raise ValueError("Number of column names must match number of values.")

        for col_name in column_names:
            self._validate_column_name(col_name)

        cols_str = ", ".join(f"`{col}`" for col in column_names)
        placeholders = ", ".join([f"@param{i}" for i in range(len(values))])
        
        query_params: List[ScalarQueryParameter] = []
        for i, current_value in enumerate(values):
            param_name = f"param{i}"
            query_params.append(self._create_scalar_query_parameter(param_name, current_value))

        query = f"""
            INSERT INTO `{self.project_id}.{self.dataset_id}.{table_id}` ({cols_str})
            VALUES ({placeholders});
        """
        job_config = QueryJobConfig(query_parameters=query_params)
        self.run_query(query, job_config=job_config)

    def delete_multiple_rows_by_id(
        self, table_id: str, id_column: str, ids: List[Any], id_value_type: str = "STRING"
    ) -> None:
        """
        Deletes multiple rows from a table based on a list of IDs using parameterized query.

        Args:
            table_id: The ID of the table.
            id_column: The name of the column containing the IDs.
            ids: A list of ID values to delete.
            id_value_type: The BigQuery type of the ID values.
        """
        if not ids:
            return # Nothing to delete
        self._validate_column_name(id_column)

        query = f"""
            DELETE FROM `{self.project_id}.{self.dataset_id}.{table_id}`
             WHERE `{id_column}` IN UNNEST(@ids);
        """
        job_config = QueryJobConfig(
            query_parameters=[
                ArrayQueryParameter("ids", id_value_type, ids)
            ]
        )
        self.run_query(query, job_config=job_config)

    def update_row_by_id(
        self,
        table_id: str,
        id_column: str,
        id_value: Any,
        column_values: Dict[str, Any],
        id_value_type: str = "STRING",
    ) -> None:
        """
        Updates specific columns of a row identified by its ID using parameterized query.

        Args:
            table_id: The ID of the table.
            id_column: The name of the column containing the ID.
            id_value: The specific ID value of the row to update.
            column_values: A dictionary where keys are column names and
                           values are the new values.
            id_value_type: The BigQuery type of the ID value.
        """
        if not column_values:
            return 
        self._validate_column_name(id_column)

        set_clauses = []
        query_params_list: List[ScalarQueryParameter] = [
            ScalarQueryParameter("id_value", id_value_type, id_value)
        ]
        
        param_idx = 0
        for col, current_value in column_values.items():
            self._validate_column_name(col)
            update_param_name = f"update_val_{param_idx}"
            set_clauses.append(f"`{col}` = @{update_param_name}")
            query_params_list.append(self._create_scalar_query_parameter(update_param_name, current_value))
            param_idx += 1
        
        if not set_clauses: # Should not happen if column_values is not empty
            return

        sets_str = ", ".join(set_clauses)
        query = f"""
            UPDATE `{self.project_id}.{self.dataset_id}.{table_id}`
            SET {sets_str}
            WHERE `{id_column}` = @id_value;
        """
        job_config = QueryJobConfig(query_parameters=query_params_list)
        self.run_query(query, job_config=job_config)

    def get_all_rows(self, table_id: str) -> RowIterator:
        """
        Retrieves all rows from the specified table.

        Args:
            table_id: The ID of the table.

        Returns:
            A RowIterator containing all rows in the table.
        """
        query = f"SELECT * FROM `{self.project_id}.{self.dataset_id}.{table_id}`"
        return self.run_query(query)

    def delete_row_by_id(self, table_id: str, id_column: str, id_value: Any, id_value_type: str = "STRING") -> None:
        """
        Deletes a single row from a table based on its ID using parameterized query.

        Args:
            table_id: The ID of the table.
            id_column: The name of the column containing the ID.
            id_value: The specific ID value of the row to delete.
            id_value_type: The BigQuery type of the ID value.
        """
        self._validate_column_name(id_column)
        query = f"""
            DELETE FROM `{self.project_id}.{self.dataset_id}.{table_id}`
             WHERE `{id_column}` = @id_value;
        """
        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("id_value", id_value_type, id_value)
            ]
        )
        self.run_query(query, job_config=job_config)
