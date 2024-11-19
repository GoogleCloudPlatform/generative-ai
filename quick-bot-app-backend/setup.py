from scripts.big_query_setup import create_dataset, create_table
from scripts.gcs_setup import create_bucket, BUCKET
from src.model.chats import Chat
from src.model.embedding import Embedding
from src.model.intent import Intent
from src.repository.big_query import BIG_QUERY_DATASET, CHATS_TABLE, EMBEDDINGS_TABLE
from src.service.intent import INTENTS_TABLE, IntentService


DEFAULT_INTENTS = [
    Intent(
        name="Code assistant",
        ai_model="gemini-1.5-flash",
        ai_temperature=1,
        description="The Coding AI Agent is your expert programming assistant",
        prompt="You are an expert coding agent. You can write, analyze, and debug code in any programming language.  You can also answer questions about code and software development concepts.  If I provide you with code, please identify the language it is written in. If I need to execute the code, I will explicitly ask you to do so.  I want you to prioritize generating concise and efficient code.  Please avoid adding unnecessary comments or explanations unless I specifically request them",
        questions=["Write a Python function to calculate the factorial of a number", "What is the difference between a stack and a queue in data structures?", "Create a simple HTML page with a button that changes color when clicked."],
        status="5",
    ),
]
INTENT_SERVICE = IntentService()

print("Setting up GCS... \n")

bucket = create_bucket(BUCKET)

print("\nSuccess!\n")

print("Setting up BigQuery... \n")

create_dataset(BIG_QUERY_DATASET)
create_table(CHATS_TABLE, Chat.__schema__())
create_table(EMBEDDINGS_TABLE, Embedding.__schema__())
create_table(INTENTS_TABLE, Intent.__schema__())

for intent in DEFAULT_INTENTS:
    try:
        INTENT_SERVICE.create(intent)
    except Exception as e:
        print(e)

print("\nSuccess!\n")