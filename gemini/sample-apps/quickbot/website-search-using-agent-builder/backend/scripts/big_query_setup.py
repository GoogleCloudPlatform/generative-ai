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
from google.cloud.bigquery import Client as BigQueryClient, Table, SchemaField, TableReference

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
    dataset_id = f"{PROJECT_ID}.{dataset_name}"
    try:
        bigquery_client.delete_dataset(
            dataset_id, delete_contents=True, not_found_ok=True
        )
        print(f"Dataset {dataset_id} deleted (if it existed).")
    except Exception as e:
        print(f"Error deleting dataset {dataset_id}: {e}")

    print(f"Creating dataset {dataset_id}...")
    bigquery_client.create_dataset(dataset_name, exists_ok=True) # exists_ok=True in case delete failed but it exists
    print(f"Dataset {dataset_id} ensured.")


def create_table(dataset: str, table_name: str, schema: List[SchemaField]):
    """Creates a BigQuery table within a specified dataset.
    If the table already exists, it will be deleted and recreated.

    Args:
        dataset: The name of the dataset where the table will be created.
        table_name: The name for the new BigQuery table.
        schema: A list of SchemaField objects defining the table's structure.
    """
    table_id_full = f"{PROJECT_ID}.{dataset}.{table_name}"
    table_ref = TableReference.from_string(table_id_full)

    try:
        bigquery_client.delete_table(table_ref, not_found_ok=True)
        print(f"Table {table_id_full} deleted (if it existed).")
    except Exception as e:
        print(f"Notice: Could not delete table {table_id_full} (may not exist or other issue): {e}")

    print(f"Creating table {table_id_full}...")
    bq_table = Table(table_ref, schema=schema)
    bigquery_client.create_table(bq_table)
    print(f"Table {table_id_full} created successfully.")
