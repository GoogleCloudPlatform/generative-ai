import os

from dotenv import load_dotenv
load_dotenv("local.env")
os.system("bash prepare_code.sh")

from google.cloud.bigquery import Client as BigQueryClient
from google.cloud.storage import Client as GCSClient

from deploy_agent_engine import setup_remote_agent
from scripts.big_query_setup import create_dataset
from scripts.big_query_setup import create_table
from scripts.big_query_setup import insert_intent
from scripts.gcs_setup import create_bucket
from src.model.chats import Chat
from src.model.embedding import Embedding
from src.model.intent import Intent
from src.repository.big_query import CHATS_TABLE
from src.repository.big_query import EMBEDDINGS_TABLE
from src.service.intent import INTENTS_TABLE

print("Setting up GCS... \n")

project_id = os.getenv("_PROJECT_ID")
location = os.getenv("_REGION")
print("ENV project_id", project_id)
print("ENV location", location)
storage_client = GCSClient()

bucket = create_bucket(f"quick-bot-{project_id}-travel-concierge-bucket", location, storage_client)

print("Setting up Remote Agent... \n")
remote_agent_resource_id = setup_remote_agent(bucket)

DEFAULT_INTENTS = [
    Intent(
        name="Travel concierge",
        ai_model="gemini-2.0-flash",
        ai_temperature=1,
        description="",
        prompt="",
        questions=[],
        status="5",
        remote_agent_resource_id=remote_agent_resource_id,
    ),
]

print(f"Successfully setted Agent. Remote agent resource ID: {remote_agent_resource_id} \n")

print("Setting up BigQuery... \n")
bigquery_client = BigQueryClient()
BIG_QUERY_DATASET = "quick_bot_app"
create_dataset(BIG_QUERY_DATASET, bigquery_client)
create_table(
    BIG_QUERY_DATASET, CHATS_TABLE, Chat.__schema__(), project_id, bigquery_client
)
create_table(
    BIG_QUERY_DATASET,
    EMBEDDINGS_TABLE,
    Embedding.__schema__(),
    project_id,
    bigquery_client,
)
create_table(
    BIG_QUERY_DATASET, INTENTS_TABLE, Intent.__schema__(), project_id, bigquery_client
)

for intent in DEFAULT_INTENTS:
    try:
        insert_intent(
            BIG_QUERY_DATASET, INTENTS_TABLE, intent.to_insert_string(), bigquery_client
        )
    except Exception as e:
        print(e)

print("\nSuccess!\n")
