"""
Initializes the BigQuery environment for the application.

This script performs the following actions:
1. Retrieves the target BigQuery dataset name from the 'BIG_QUERY_DATASET'
   environment variable.
2. Creates the specified BigQuery dataset if it doesn't already exist.
3. Creates the 'search_applications' table within that dataset, using the
   schema defined by the `SearchApplication` model, if the table doesn't
   already exist.

Usage:
    Run this script directly (e.g., `python setup.py`) to set up the
    necessary BigQuery resources. Ensure the 'BIG_QUERY_DATASET' environment
    variable is set beforehand.
"""

from os import getenv
from scripts.big_query_setup import create_dataset, create_table
from src.service.search_application import SEARCH_APPLICATION_TABLE
from src.model.search import SearchApplication

# BIG_QUERY_DATASET=""
BIG_QUERY_DATASET = getenv("BIG_QUERY_DATASET")

print("Setting up BigQuery... \n")

create_dataset(BIG_QUERY_DATASET)
create_table(
    BIG_QUERY_DATASET, SEARCH_APPLICATION_TABLE, SearchApplication.__schema__()
)

print("\nSuccess!\n")
