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

from scripts.big_query_setup import create_dataset, create_table
from src.service.search_application import SEARCH_APPLICATION_TABLE
from src.model.search import SearchApplication

BIG_QUERY_DATASET = ""

if not BIG_QUERY_DATASET: # Extra check in case the default was also empty or env var was set to empty
    raise ValueError("BIGQUERY_DATASET_ID resolved to an empty string. Please ensure it's set correctly.")

create_dataset(BIG_QUERY_DATASET)
create_table(
    BIG_QUERY_DATASET, SEARCH_APPLICATION_TABLE, SearchApplication.__schema__()
)

print("\nSuccess!\n")
