from typing import List
from google.api_core.exceptions import NotFound
from google.cloud.bigquery import Client as BigQueryClient, Table, SchemaField
from src.repository.big_query import BIG_QUERY_DATASET

bigquery_client = BigQueryClient()
PROJECT_ID = bigquery_client.project

def create_dataset(dataset_name: str):
    bigquery_client.delete_dataset(dataset_name, delete_contents=True, not_found_ok=True)
    print(f"{dataset_name} Creating dataset...")
    bigquery_client.create_dataset(dataset_name)

def create_table(table_name: str, schema: List[SchemaField]):
    bigquery_client.create_table(Table(f"{PROJECT_ID}.{BIG_QUERY_DATASET}.{table_name}", schema))