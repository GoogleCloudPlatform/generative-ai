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

from typing import List

from google.cloud.bigquery import Client
from google.cloud.bigquery import SchemaField
from google.cloud.bigquery import Table


def create_dataset(dataset_name: str, bigquery_client: Client):
    bigquery_client.delete_dataset(
        dataset_name, delete_contents=True, not_found_ok=True
    )
    print(f"{dataset_name} Creating dataset...")
    bigquery_client.create_dataset(dataset_name)


def create_table(
    dataset: str,
    table_name: str,
    schema: List[SchemaField],
    project_id: str,
    bigquery_client,
):
    bigquery_client.create_table(Table(f"{project_id}.{dataset}.{table_name}", schema))


def insert_intent(dataset: str, table_name: str, values: str, bigquery_client: Client):
    bigquery_client.query(
        f"""
                INSERT INTO `{dataset}.{table_name}` 
                VALUES({values});
            """
    ).result()
