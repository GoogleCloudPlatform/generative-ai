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

from typing import Dict, List
from google.cloud.bigquery import Client
import logging

from src.models import Embedding

BIG_QUERY_DATASET=""

EMBEDDINGS_TABLE = "embeddings"
EMBEDDINGS_ID_COLUMN = "id"
EMBEDDINGS_TEXT_COLUMN = "text"
EMBEDDINGS_INDEX_COLUMN = "index"

INTENTS_TABLE = "intents"
INTENTS_TABLE_ID_COLUMN = "name"
INTENTS_TABLE_STATUS_COLUMN = "status"


class BigQueryRepository:

    def __init__(self):
        self.client: Client = Client()

    def run_query(self, query: str):
        logging.info(query)
        return self.client.query(query).result()
    
    def get_row_by_id(self, table_id: str, id_column: str, id: str):
        query = f"""
                SELECT * FROM `{BIG_QUERY_DATASET}.{table_id}` 
                WHERE {id_column} = "{id}";
            """
        return self.run_query(query)

    def insert_rows(self, table_id: str, embeddings: List[Embedding]):
        values = [embedding.to_dict() for embedding in embeddings]
        errors = self.client.insert_rows(f"{BIG_QUERY_DATASET}.{table_id}", values, Embedding.__schema__())
        if errors == []:
            print("Embeddings added")
        else:
            print("Encountered errors while inserting rows: {}".format(errors))
            raise(Exception("Error inserting embeddings in BQ"))

    def update_intent_status(self, intent_name: str, intent_status: str):
        query = f"""
            UPDATE `{BIG_QUERY_DATASET}.{INTENTS_TABLE}` 
            SET {INTENTS_TABLE_STATUS_COLUMN} = "{intent_status}"
            WHERE {INTENTS_TABLE_ID_COLUMN} = "{intent_name}"
            """
        return self.run_query(query)