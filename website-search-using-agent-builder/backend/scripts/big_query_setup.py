"""Utility functions for setting up Google BigQuery datasets and tables."""

from typing import List
from google.cloud.bigquery import Client as BigQueryClient, Table, SchemaField

bigquery_client = BigQueryClient()
PROJECT_ID = bigquery_client.project


def create_dataset(dataset_name: str):
    """Deletes an existing BigQuery dataset and recreates it.

    If the dataset already exists, it and all its contents will be deleted first.
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
