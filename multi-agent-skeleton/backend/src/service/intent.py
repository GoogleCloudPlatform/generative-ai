from src.model.http_status import BadRequest
from src.model.intent import Intent
from src.repository.big_query import BIG_QUERY_DATASET, BigQueryRepository
from src.repository.cloud_storage import CloudStorageRepository
from typing import List

INTENTS_TABLE = "intents"
INTENTS_TABLE_ID_COLUMN = "name"

class IntentService:

    def __init__(self):
        self.repository = BigQueryRepository()
        self.gcs_repository = CloudStorageRepository()

    def get(self, intent_name: str):
        intent = None
        results = self.repository.run_query(f'SELECT * FROM `{BIG_QUERY_DATASET}.{INTENTS_TABLE}` WHERE name = "{intent_name}"')
        for row in results:
            intent = Intent.__from_row__(row)

        return intent

    def get_all(self) -> List[Intent]:
        intents = []
        print(f"[IntentService - get_all - BIG_QUERY_DATASET]: {BIG_QUERY_DATASET}")
        print(f"[IntentService - get_all - INTENTS_TABLE]: {INTENTS_TABLE}")
        results = self.repository.run_query(f"SELECT * FROM `{BIG_QUERY_DATASET}.{INTENTS_TABLE}`")
        for row in results:
            intent = Intent.__from_row__(row)
            intents.append(intent)

        return intents

    def create(self, intent: Intent) -> Intent:
        if self.get(intent.name):
            raise BadRequest(detail=f"Intent with name {intent.name} already exists")
        if intent.gcp_bucket and not self.gcs_repository.list(intent.gcp_bucket):
            raise BadRequest(detail=f"No data found on {intent.gcp_bucket}, please, add your pdf files in the proper location.")
        if not intent.gcp_bucket:
            intent.status = "5"
        self.repository.insert_row(INTENTS_TABLE, intent.to_insert_string())
        return intent
    
    def update(self, intent_name: str, intent: Intent):
        update_dict = {
            'ai_model': f'"{intent.ai_model}"',
            'ai_temperature': f'{intent.ai_temperature}',
            'description': f'"{intent.description}"',
            'prompt': f'"""{intent.prompt}"""',
            'questions': f'{str(intent.questions)}',
            'status': f'"{intent.status}"',
        }
        self.repository.update_row_by_id(INTENTS_TABLE, INTENTS_TABLE_ID_COLUMN, intent_name, update_dict)

    def delete(self, intent_name: str):
        self.repository.delete_row_by_id(INTENTS_TABLE, INTENTS_TABLE_ID_COLUMN, intent_name)