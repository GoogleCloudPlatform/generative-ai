import os

from dotenv import load_dotenv

from deploy import setup_remote_agent
from scripts.big_query_setup import create_dataset
from scripts.big_query_setup import create_table
from scripts.big_query_setup import insert_intent
from scripts.gcs_setup import BUCKET
from scripts.gcs_setup import create_bucket
from src.model.chats import Chat
from src.model.embedding import Embedding
from src.model.intent import Intent
from src.repository.big_query import CHATS_TABLE
from src.repository.big_query import EMBEDDINGS_TABLE
from src.service.intent import INTENTS_TABLE

load_dotenv()

BIG_QUERY_DATASET = ""

os.system("./prepare_code.sh")

remote_agent_resource_id = setup_remote_agent()

DEFAULT_INTENTS = [
    Intent(
        name="Travel concierge",
        ai_model="gemini-2.0-flash",
        ai_temperature=1,
        description="ADK sample template",
        prompt="",
        questions=[],
        status="5",
        remote_agent_resource_id=remote_agent_resource_id,
    ),
]

print("Remote agent resource ID: " + remote_agent_resource_id + "\n")

print("Setting up GCS... \n")

bucket = create_bucket(BUCKET)

print("\nSuccess!\n")

print("Setting up BigQuery... \n")

create_dataset(BIG_QUERY_DATASET)
create_table(BIG_QUERY_DATASET, CHATS_TABLE, Chat.__schema__())
create_table(BIG_QUERY_DATASET, EMBEDDINGS_TABLE, Embedding.__schema__())
create_table(BIG_QUERY_DATASET, INTENTS_TABLE, Intent.__schema__())

for intent in DEFAULT_INTENTS:
    try:
        insert_intent(BIG_QUERY_DATASET, INTENTS_TABLE, intent.to_insert_string())
    except Exception as e:
        print(e)

print("\nSuccess!\n")
