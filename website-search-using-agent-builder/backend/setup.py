import os
from scripts.big_query_setup import create_dataset, create_table
from src.service.search_application import SEARCH_APPLICATION_TABLE
from src.model.search import SearchApplication

# Get the BigQuery Dataset ID from an environment variable
BIG_QUERY_DATASET = os.environ.get("BIGQUERY_DATASET_ID", "eren")

print(f"Setting up BigQuery for dataset: '{BIG_QUERY_DATASET}'... \n")

if not BIG_QUERY_DATASET: # Extra check in case the default was also empty or env var was set to empty
    raise ValueError("BIGQUERY_DATASET_ID resolved to an empty string. Please ensure it's set correctly.")

create_dataset(BIG_QUERY_DATASET)
create_table(BIG_QUERY_DATASET, SEARCH_APPLICATION_TABLE, SearchApplication.__schema__())

print("\nSuccess!\n")