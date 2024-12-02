from scripts.big_query_setup import create_dataset, create_table, insert_intent
from scripts.gcs_setup import create_bucket, BUCKET
from src.model.chats import Chat
from src.model.embedding import Embedding
from src.model.intent import Intent
from src.repository.big_query import CHATS_TABLE, EMBEDDINGS_TABLE
from src.service.intent import INTENTS_TABLE

BIG_QUERY_DATASET=""

print("Setting up GCS... \n")

bucket = create_bucket(BUCKET)

print("\nSuccess!\n")

print("Setting up BigQuery... \n")

create_dataset(BIG_QUERY_DATASET)
create_table(BIG_QUERY_DATASET, CHATS_TABLE, Chat.__schema__())
create_table(BIG_QUERY_DATASET, EMBEDDINGS_TABLE, Embedding.__schema__())
create_table(BIG_QUERY_DATASET, INTENTS_TABLE, Intent.__schema__())

print("\nSuccess!\n")