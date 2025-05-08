import os

from dotenv import load_dotenv
# load_dotenv("local.env")
# os.system("bash prepare_code.sh")

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

try:
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
    BIG_QUERY_DATASET = os.getenv("BIG_QUERY_DATASET") if os.getenv("BIG_QUERY_DATASET") else os.getenv("_CHATBOT_NAME", "quickbot").lower().replace(" ", "_").replace("-","_")
    print(f"Setting up BigQuery Dataset {BIG_QUERY_DATASET}... \n")
    create_dataset(BIG_QUERY_DATASET, bigquery_client)

    print(f"Setting up BigQuery Table {CHATS_TABLE}... \n")
    create_table(
        BIG_QUERY_DATASET, CHATS_TABLE, Chat.__schema__(), project_id, bigquery_client
    )
    print(f"Setting up BigQuery Table {EMBEDDINGS_TABLE}... \n")
    create_table(
        BIG_QUERY_DATASET,
        EMBEDDINGS_TABLE,
        Embedding.__schema__(),
        project_id,
        bigquery_client,
    )
    print(f"Setting up BigQuery Table {INTENTS_TABLE}... \n")
    create_table(
        BIG_QUERY_DATASET, INTENTS_TABLE, Intent.__schema__(), project_id, bigquery_client
    )

    for intent in DEFAULT_INTENTS:
        try:
            insert_intent(
                BIG_QUERY_DATASET, INTENTS_TABLE, intent.to_insert_string(), bigquery_client
            )
            print(f"Intent 'Travel concierge' created successfully \n")
        except Exception as e:
            print(e)
            print(f"An error occurred during the setup process: {e}")
            print(f"ERROR: A command in the backend setup block failed with code {e.returncode}.")
            if e.stdout: print(f"Stdout from failed command:\n{e.stdout}")
            else: print("Stdout from failed command: <empty>")
            if e.stderr: print(f"Stderr from failed command:\n{e.stderr}")
            else: print("Stderr from failed command: <empty>")

    print("\nSuccess!\n")
except Exception as e:
    print(f"An error occurred during the setup process: {e}")
    print(f"ERROR: A command in the backend setup block failed with code {e.returncode}.")
    if e.stdout: print(f"Stdout from failed command:\n{e.stdout}")
    else: print("Stdout from failed command: <empty>")
    if e.stderr: print(f"Stderr from failed command:\n{e.stderr}")
    else: print("Stderr from failed command: <empty>")
    # You could also include a traceback for more detailed error information:
    import traceback
    print(traceback.format_exc())
