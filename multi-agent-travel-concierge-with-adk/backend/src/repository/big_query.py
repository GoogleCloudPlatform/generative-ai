from os import getenv
from typing import Dict, List
from google.cloud.bigquery import Client

BIG_QUERY_DATASET = getenv("BIG_QUERY_DATASET")
print("BIG_QUERY_DATASET", BIG_QUERY_DATASET)

CHATS_TABLE = 'chats'
CHATS_ID_COLUMN = "id"

EMBEDDINGS_TABLE = "embeddings"
EMBEDDINGS_ID_COLUMN = "id"
EMBEDDINGS_TEXT_COLUMN = "text"
EMBEDDINGS_INDEX_COLUMN = "index"


class BigQueryRepository:

    def __init__(self):
        self.client: Client = Client()

    def run_query(self, query: str):
        print(query)
        return self.client.query(query).result()
    
    def get_row_by_id(self, table_id: str, id_column: str, id: str):
        query = f"""
                SELECT * FROM `{BIG_QUERY_DATASET}.{table_id}` 
                WHERE {id_column} = "{id}";
            """
        return self.run_query(query)
    
    def insert_row(self, table_id: str, values: str):
        query = f"""
                INSERT INTO `{BIG_QUERY_DATASET}.{table_id}` 
                VALUES({values});
            """
        return self.run_query(query)
    
    def delete_multiple_rows_by_id(self, table_id: str, id_column: str, ids: List[str]):
        return self.run_query(
            f"""
                DELETE FROM `{BIG_QUERY_DATASET}.{table_id}`
                WHERE {id_column} IN UNNEST([{', '.join(f'"{id}"' for id in ids)}]);
            """
        )
    
    def update_row_by_id(self, table_id: str, id_column: str, id: str, column_value: Dict[str, str]):
        sets = ""
        for k, v in column_value.items():
            sets += f"{k}={v},"
        sets = sets[:-1]
        query = f"""
                UPDATE `{BIG_QUERY_DATASET}.{table_id}` 
                SET {sets} 
                WHERE {id_column} = "{id}";
            """
        return self.run_query(query)
    
    def get_all_rows(self, table_id: str):
        query = f"""
                    SELECT * from `{BIG_QUERY_DATASET}.{table_id}`
                """
        return self.run_query(query)
    
    def delete_row_by_id(self, table_id: str, id_column: str, id: str):
        query = f"""
                DELETE FROM `{BIG_QUERY_DATASET}.{table_id}`
                WHERE {id_column} = "{id}"
            """
        return self.run_query(query)