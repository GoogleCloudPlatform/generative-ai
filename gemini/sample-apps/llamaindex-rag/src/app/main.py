from datetime import datetime
import json
import logging
import os
from pathlib import Path
from typing import Any, Iterator, List, Optional, Sequence, Tuple, Union, cast
import uuid

from common.common import DATA_PATH
from common.utils import download_blob
from datasets import Dataset
from fastapi import Depends, FastAPI, HTTPException
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import PermissionDenied
import google.auth
import google.auth.transport.requests
from google.cloud import (
    aiplatform,
    firestore,
    firestore_admin_v1,
    secretmanager,
    storage,
)
from google.oauth2 import service_account
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
import pandas as pd
from pydantic import BaseModel

# Ragas must be 0.9.1
from ragas import evaluate
from ragas.metrics import (
    answer_correctness,
    answer_relevancy,
    answer_similarity,
    context_precision,
    context_recall,
    context_relevancy,
    faithfulness,
)
from src.rag.evaluate import LLMEvaluator, write_results_to_bq
import uvicorn
import yaml

logging.basicConfig(
    filename="eval.log", encoding="utf-8", level=logging.INFO
)  # Set the desired logging level
logger = logging.getLogger(__name__)

config_path = os.path.join(
    os.path.dirname(__file__), "..", "..", "common", "config.yaml"
)
with open(config_path, "r") as config_file:
    config = yaml.safe_load(config_file)

# Now you can use the processed paths
PROJECT_ID = config["project_id"]
SERVICE_ACCOUNT_KEY = config["service_account_key"]
FIRESTORE_DB_NAME = config.get("firestore_db_name")


ragas_metrics_dict = {
    "context_precision": context_precision,
    "answer_relevancy": answer_relevancy,
    "faithfulness": faithfulness,
    "context_relevancy": context_relevancy,
    "context_recall": context_recall,
    "answer_similarity": answer_similarity,
    "answer_correctness": answer_correctness,
}


def get_secret(project_id, secret_id, version_id="latest"):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("UTF-8")


class IndexUpdate(BaseModel):
    base_index_name: str
    base_endpoint_name: str
    qa_index_name: Optional[str]
    qa_endpoint_name: Optional[str]
    firestore_db_name: Optional[str]
    firestore_namespace: Optional[str]


class PromptUpdate(BaseModel):
    prompt_name: str
    new_content: str


class RAGConfig(BaseModel):
    llm_name: str = "gemini-1.5-flash"
    temperature: float = 0.2
    similarity_top_k: int = 5
    retrieval_strategy: str = "auto_merging"
    use_hyde: bool = True
    use_refine: bool = True
    use_node_rerank: bool = True
    use_react: bool = True
    qa_followup: bool = True
    hybrid_retrieval: bool = True


class RAGRequest(RAGConfig):
    query: str = "What were Google's Q1 Earnings?"
    evaluate_response: bool
    eval_model_name: Optional[str] = "gemini-1.5-flash"
    embedding_model_name: Optional[str] = "text-embedding-004"


class EvalRequest(RAGConfig):
    eval_model_name: str = "gemini-1.5-flash"
    embedding_model_name: Optional[str] = "text-embedding-004"
    input_eval_dataset_bucket_uri: str = "test_rag_questions/test_ground_truth.csv"
    bq_eval_results_table_id: str = "eval_results.eval_results_table"
    ragas_metrics: List[str] = ["faithfulness", "answer_relevancy"]


# Shared state - to be updated by UI
from src.app.shared_state import index_manager, prompts


def get_index_manager():
    logger.info(index_manager.base_index.docstore)
    logger.info(index_manager.firestore_db_name)
    logger.info(index_manager.firestore_namespace)
    return index_manager


def get_prompts():
    return prompts


creds = google.auth.default()[0]
request = google.auth.transport.requests.Request()

app = FastAPI()


@app.get("/")
def root():
    return {"hello world": "hello world"}


@app.get("/get_all_prompts")
async def get_all_prompts(prompts=Depends(get_prompts)):
    return prompts.to_dict()


@app.post("/update_prompt")
async def update_prompt(prompt_update: PromptUpdate, prompts=Depends(get_prompts)):
    try:
        prompts.update(prompt_update.prompt_name, prompt_update.new_content)
        return {"message": f"Prompt {prompt_update.prompt_name} updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/list_vector_search_indexes")
async def list_vector_search_indexes(
    qa_or_base: dict, index_manager=Depends(get_index_manager)
):
    index_list = aiplatform.MatchingEngineIndex.list()
    index_list = [i.display_name for i in index_list]
    if qa_or_base["qa_or_base"] == "qa":
        active_index_name = index_manager.qa_index_name
    elif qa_or_base["qa_or_base"] == "base":
        active_index_name = index_manager.base_index_name
    if active_index_name is None:
        index_list.insert(0, None)
    else:
        index_list.remove(active_index_name)
        index_list.insert(0, active_index_name)
    return index_list


@app.post("/list_vector_search_endpoints")
async def list_vector_search_endpoints(
    qa_or_base: dict, index_manager=Depends(get_index_manager)
):
    endpoint_list = aiplatform.MatchingEngineIndexEndpoint.list()
    endpoint_list = [e.display_name for e in endpoint_list]
    if qa_or_base["qa_or_base"] == "qa":
        active_endpoint_name = index_manager.qa_endpoint_name
    elif qa_or_base["qa_or_base"] == "base":
        active_endpoint_name = index_manager.base_endpoint_name
    if active_endpoint_name is None:
        endpoint_list.insert(0, None)
    else:
        endpoint_list.remove(active_endpoint_name)
        endpoint_list.insert(0, active_endpoint_name)
    return endpoint_list


@app.get("/list_firestore_databases")
async def list_firestore_databases(index_manager=Depends(get_index_manager)):
    active_db_name = index_manager.firestore_db_name
    client_options = ClientOptions(api_endpoint="firestore.googleapis.com")
    client = firestore_admin_v1.FirestoreAdminClient(client_options=client_options)
    parent = f"projects/{index_manager.project_id}"
    databases = []

    try:
        # List all databases in the project
        for database in client.list_databases(parent=parent).databases:
            databases.append(database.name.split("/")[-1])
        logger.info(databases)
        if active_db_name is None:
            databases.insert(0, None)
        else:
            databases.remove(active_db_name)
            databases.insert(0, active_db_name)
        return databases

    except Exception as e:
        logger.info(f"An error occurred: {e}")
        return []


@app.post("/list_firestore_collections")
async def list_firestore_collections(
    db_name: dict, index_manager=Depends(get_index_manager)
):
    """
    List all collections in a Firestore database.

    :param project_id: Your Google Cloud project ID
    :param database_id: The database ID. Use "(default)" for the default database.
    :return: A list of collection IDs
    """

    def get_prefixes(string_list):
        suffixes = ["_metadata", "_data", "_ref_doc_info"]
        prefixes = []

        for s in string_list:
            for suffix in suffixes:
                if s.endswith(suffix):
                    prefixes.append(s[: -len(suffix)])
                    break
            else:
                prefixes.append(s)

        return prefixes

    # Initialize Firestore client
    if db_name["firestore_db_name"]:
        db = firestore.Client(
            project=index_manager.project_id, database=db_name["firestore_db_name"]
        )
    else:
        return []
    try:
        # Get all collections
        collections = db.collections()
        collection_info = [collection.id for collection in collections]
        collection_info = list(set(get_prefixes(collection_info)))
        active_firestore_namespace = index_manager.firestore_namespace
        if active_firestore_namespace is None:
            collection_info.insert(0, None)
        else:
            collection_info.remove(active_firestore_namespace)
            collection_info.insert(0, active_firestore_namespace)
        return collection_info

    except PermissionDenied:
        print(
            f"Permission denied. Make sure you have the necessary permissions to access Firestore in project {PROJECT_ID}"
        )
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


@app.get("/get_current_index_info")
async def get_current_index_info(index_manager=Depends(get_index_manager)):
    return index_manager.get_current_index_info()


@app.post("/update_index")
async def update_index(
    index_update: IndexUpdate, index_manager=Depends(get_index_manager)
):
    try:
        index_manager.set_current_indexes(
            index_update.base_index_name,
            index_update.base_endpoint_name,
            index_update.qa_index_name,
            index_update.qa_endpoint_name,
            index_update.firestore_db_name,
            index_update.firestore_namespace,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/query_rag")
async def query_rag(
    rag_request: RAGRequest,
    index_manager=Depends(get_index_manager),
    prompts=Depends(get_prompts),
):
    query_engine = index_manager.get_query_engine(
        prompts=prompts,
        llm_name=rag_request.llm_name,
        temperature=rag_request.temperature,
        similarity_top_k=rag_request.similarity_top_k,
        retrieval_strategy=rag_request.retrieval_strategy,
        use_hyde=rag_request.use_hyde,
        use_refine=rag_request.use_refine,
        use_node_rerank=rag_request.use_node_rerank,
        qa_followup=rag_request.qa_followup,
        hybrid_retrieval=rag_request.hybrid_retrieval,
    )
    if rag_request.use_react:
        react_agent = index_manager.get_react_agent(
            prompts=prompts,
            llm_name=rag_request.llm_name,
            temperature=rag_request.temperature,
        )
        response = await react_agent.achat(rag_request.query)
    else:
        response = await query_engine.aquery(rag_request.query)
    if rag_request.evaluate_response:
        # Evaluate response with ragas against metrics
        retrieved_contexts = [r.node.text for r in response.source_nodes]
        eval_df = pd.DataFrame(
            {
                "question": rag_request.query,
                "answer": [response.response],
                "contexts": [retrieved_contexts],
            }
        )
        eval_df_ds = Dataset.from_pandas(eval_df)

        # create Langchain LLM and Embeddings
        vertextai_llm = ChatVertexAI(
            credentials=creds, model_name=rag_request.eval_model_name
        )
        vertextai_embeddings = VertexAIEmbeddings(
            credentials=creds, model_name=rag_request.embedding_model_name
        )

        # No ground truth so can only do answer_relevancy, faithfulness and context_relevancy
        metrics = [answer_relevancy, faithfulness, context_relevancy]
        result = evaluate(
            eval_df_ds,
            metrics=metrics,
            llm=vertextai_llm,
            embeddings=vertextai_embeddings,
        )
        result_dict = (
            result.to_pandas()[
                ["answer_relevancy", "faithfulness", "context_relevancy"]
            ]
            .fillna(0)
            .iloc[0]
            .to_dict()
        )
        retrieved_context_dict = {"retreived_chunks": response.source_nodes}
        logger.info(result_dict)
        return {"response": response.response} | result_dict | retrieved_context_dict
    else:
        return {"response": response.response}


@app.post("/eval_batch")
def eval_batch(
    eval_batch_request: EvalRequest,
    index_manager=Depends(get_index_manager),
    prompts=Depends(get_prompts),
):
    query_engine = index_manager.get_query_engine(
        prompts=prompts,
        llm_name=eval_batch_request.llm_name,
        temperature=eval_batch_request.temperature,
        similarity_top_k=eval_batch_request.similarity_top_k,
        retrieval_strategy=eval_batch_request.retrieval_strategy,
        use_hyde=eval_batch_request.use_hyde,
        use_refine=eval_batch_request.use_refine,
        use_node_rerank=eval_batch_request.use_node_rerank,
        qa_followup=eval_batch_request.qa_followup,
        hybrid_retrieval=eval_batch_request.hybrid_retrieval,
    )
    bucket_name = eval_batch_request.input_eval_dataset_bucket_uri.split("/")[0]
    file_name = "/".join(
        eval_batch_request.input_eval_dataset_bucket_uri.split("/")[1:]
    )
    logger.info(bucket_name)
    logger.info(file_name)
    download_blob(bucket_name, file_name, "ground_truth.csv")
    eval_df = pd.read_csv("./ground_truth.csv")
    eval_df = eval_df[["question", "ground_truth"]]
    eval_df = eval_df.astype({"question": str, "ground_truth": str})
    logging.info(eval_df.dtypes)

    llm_evaluator = LLMEvaluator(
        system_prompt=prompts.eval_prompt_wcontext_system,
        user_prompt=prompts.eval_prompt_wcontext_user,
        eval_model_name=eval_batch_request.eval_model_name,
        temperature=eval_batch_request.temperature,
    )

    if eval_batch_request.use_react:
        react_agent = index_manager.get_react_agent(
            prompts=prompts,
            llm_name=eval_batch_request.llm_name,
            temperature=eval_batch_request.temperature,
        )
        llm_evaluator.evaluate(react_agent.achat, eval_df)
    else:
        # Model-graded eval
        eval_df = llm_evaluator.evaluate(query_engine.aquery, eval_df)

    # create Langchain LLM and Embeddings
    vertextai_llm = ChatVertexAI(
        credentials=creds, model_name=eval_batch_request.eval_model_name
    )
    vertextai_embeddings = VertexAIEmbeddings(
        credentials=creds, model_name=eval_batch_request.embedding_model_name
    )
    eval_df = eval_df.rename(columns={"retrieved_context": "contexts"})
    eval_df_ds = Dataset.from_pandas(eval_df)
    logger.info(eval_df.columns)

    # Ragas eval
    metrics = []
    for m in eval_batch_request.ragas_metrics:
        metrics.append(ragas_metrics_dict[m])
    result = evaluate(
        eval_df_ds, metrics=metrics, llm=vertextai_llm, embeddings=vertextai_embeddings
    )
    ragas_results_df = result.to_pandas()[eval_batch_request.ragas_metrics].fillna(0)
    # eval_df must have schema "question", "answer", "ground_truth", "eval_result", "score"
    eval_uuid = str(uuid.uuid4())
    eval_df["date_time"] = datetime.now()
    eval_df["eval_uuid"] = eval_uuid
    eval_df["retrieval_strategy"] = eval_batch_request.retrieval_strategy
    eval_df["eval_model_name"] = eval_batch_request.eval_model_name
    eval_df["similarity_top_k"] = eval_batch_request.similarity_top_k
    eval_df["llm_model_name"] = eval_batch_request.llm_name
    eval_df["question_idx"] = eval_df.index

    eval_df = pd.concat([eval_df, ragas_results_df], axis=1)
    logging.info(eval_df.to_dict(orient="list"))

    # write_results_to_bq(eval_df, table_id=eval_batch_request.bq_eval_results_table_id)
    logging.info(f"EVAL ID: {eval_uuid}")
    return eval_df.to_dict(orient="list")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8033)


# creds, _ = google.auth.default()
# request = google.auth.transport.requests.Request()
# creds.refresh(request)
# print("Credentials:", creds)

# # Define the required scopes
# scopes = ["https://www.googleapis.com/auth/cloud-platform"]

# # Load credentials and specify scopes
# creds = service_account.Credentials.from_service_account_file(
#    "/app/credentials.json", scopes=scopes
# )

# Retrieve the service account key JSON from Secret Manager
# service_account_key_json = get_secret(PROJECT_ID, SERVICE_ACCOUNT_KEY)

# # Parse the JSON string into a dictionary
# service_account_info = json.loads(service_account_key_json)

# # Define the required scopes
# scopes = ["https://www.googleapis.com/auth/cloud-platform"]

# # Create credentials from the service account info
# creds = service_account.Credentials.from_service_account_info(
#     service_account_info, scopes=scopes
# )
