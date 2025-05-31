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

"""Utility functions for setting up Google BigQuery datasets and tables."""

from typing import List
from google.cloud.bigquery import Client as BigQueryClient, Table, SchemaField

bigquery_client = BigQueryClient()
PROJECT_ID = bigquery_client.project


def create_dataset(dataset_name: str):
    """Deletes an existing BigQuery dataset and recreates it.

    If the dataset already exists, it and all its contents
    will be deleted first.
    Then, a new empty dataset with the specified name is created.

    Args:
        dataset_name: The name for the BigQuery dataset.
    """
    bigquery_client.delete_dataset(
        dataset_name, delete_contents=True, not_found_ok=True
    )
    print(f"{dataset_name} Creating dataset...")
    bigquery_client.create_dataset(dataset_name)


def create_table(dataset: str, table_name: str, schema: List[SchemaField]):
    """Creates a BigQuery table within a specified dataset.

    Args:
        dataset: The name of the dataset where the table will be created.
        table_name: The name for the new BigQuery table.
        schema: A list of SchemaField objects defining the table's structure.
    """
    bigquery_client.create_table(
        Table(f"{PROJECT_ID}.{dataset}.{table_name}", schema)
    )


def insert_intent(dataset: str, table_name: str, values: str):
    """Inserts a single row into the specified BigQuery table using raw values.

    Constructs and executes an INSERT SQL query to add a new record.

    Args:
        dataset: The name of the BigQuery dataset.
        table_name: The name of the target BigQuery table (the intents table).
        values: A string representing the row values, formatted as required by
                BigQuery INSERT syntax (e.g., "'string_val', 123, TRUE").
                The caller is responsible for correct formatting, quoting, and
                ensuring the order matches the table schema.
    """
    bigquery_client.query(
        f"""
                INSERT INTO `{dataset}.{table_name}` VALUES({values});
            """
    ).result()
