import ast
import base64
import json
import os

import functions_framework
from cloudevents.http.event import CloudEvent
from dotenv import load_dotenv
from google.cloud import firestore
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

load_dotenv()


class WatchdogResult(BaseModel):
    matched: bool = Field(
        description="True if the prompt condition is met, False otherwise"
    )
    reasoning: str = Field(
        description="Brief explanation of why it matched or did not match"
    )


llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    temperature=0,
    max_tokens=1024,
    vertexai=True,
)
if __name__ == "__main__":
    # result = llm.invoke("hello how r u ")
    # print(result.content_blocks[0]['text'])
    pass


# {'message_id': '008', 'timestamp': '2023-12-23T10:12:00Z',
#  'sender': 'buyer456', 'text': 'GOALLL'}

db = firestore.Client(
    database=os.getenv("FIRESTORE_DATABASE"),
    project=os.getenv("GCP_PROJECT")
)


def fetch_active_prompts_from_firestore():
    # Fetch all prompts where status is 'active'
    collection = os.getenv("FIRESTORE_COLLECTION", "prompts")
    docs = db.collection(collection).where("status", "==", "active").stream()
    prompts = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        prompts.append(data)
    return prompts


@functions_framework.cloud_event
def subscribe(cloud_event: CloudEvent) -> None:
    print("Evaluating incoming Pub/Sub message")
    try:
        msg_data = cloud_event.data["message"]["data"]
        decoded_str = base64.b64decode(msg_data).decode("utf-8")

        try:
            # 1. Try parsing as standard JSON
            message_dict = json.loads(decoded_str)
        except Exception:
            try:
                # 2. Fallback to literal_eval for Python-style dicts
                # (e.g., using single quotes)
                message_dict = ast.literal_eval(decoded_str)
            except Exception:
                # 3. If all parsing fails, set to None so it gets wrapped below
                message_dict = None

        # 4. If the payload parsed to a string/list/number instead of
        # a dict, or failed to parse entirely, wrap it
        if not isinstance(message_dict, dict):
            message_dict = {"text": decoded_str}

        message_text = message_dict.get("text", "")
    except Exception as e:
        print(
            json.dumps(
                {"event": "error", "message": f"Failed to parse message: {e}"}
            )
        )
        return

    try:
        prompts = fetch_active_prompts_from_firestore()
        print(f"Found {len(prompts)} active watchdogs")
    except Exception as e:
        print(
            json.dumps(
                {
                    "event": "error",
                    "message": f"Error fetching prompts from Firestore: {e}",
                }
            )
        )
        return

    # Initialize structured output LLM
    structured_llm = llm.with_structured_output(WatchdogResult)

    for active_prompt in prompts:
        template = active_prompt.get("content", "")
        name = active_prompt.get("name", "unnamed")
        watchdog_id = active_prompt["id"]

        try:
            prompt_template = PromptTemplate.from_template(template)
            chain = prompt_template | structured_llm

            # Evaluate
            result = chain.invoke({"text": message_text})

            # Structured JSON Log for GCP Metrics
            matched = False
            reasoning = ""
            if isinstance(result, WatchdogResult):
                matched = result.matched
                reasoning = result.reasoning
            elif isinstance(result, dict):
                matched = result.get("matched", False)
                reasoning = result.get("reasoning", "")

            log_entry = {
                "event": "watchdog_evaluation",
                "watchdog_id": watchdog_id,
                "watchdog_name": name,
                "matched": matched,
                "reasoning": reasoning,
                "message_id": message_dict.get("message_id"),
            }
            print(json.dumps(log_entry))

        except Exception as e:
            print(
                json.dumps(
                    {
                        "event": "watchdog_error",
                        "watchdog_id": watchdog_id,
                        "watchdog_name": name,
                        "error": str(e),
                    }
                )
            )
