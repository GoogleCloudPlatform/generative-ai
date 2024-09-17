from backend.app.main import app
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client():
    return TestClient(app)


# Define parameter combinations for query_rag
query_rag_params = [
    {
        "llm_name": "gemini-1.5-flash",
        "temperature": 0.2,
        "similarity_top_k": 2,
        "retrieval_strategy": "auto_merging",
        "use_hyde": True,
        "use_refine": True,
        "use_node_rerank": True,
        "use_react": False,
        "qa_followup": True,
        "hybrid_retrieval": True,
        "query": "What were Google's Q1 Earnings?",
        "evaluate_response": True,
        "eval_model_name": "gemini-1.5-flash",
        "embedding_model_name": "text-embedding-004",
    }
]


@pytest.mark.parametrize("payload", query_rag_params)
def test_query_rag(client, payload):
    response = client.post("/query_rag", json=payload)
    assert response.status_code == 200


eval_batch_params = [
    {
        "llm_name": "gemini-1.5-flash",
        "temperature": 0.2,
        "similarity_top_k": 5,
        "retrieval_strategy": "parent",
        "use_hyde": True,
        "use_refine": True,
        "use_node_rerank": False,
        "use_react": False,
        "eval_model_name": "gemini-1.5-flash",
        "embedding_model_name": "text-embedding-004",
        "input_eval_dataset_bucket_uri": "rag-llm-bucket/test_ground_truth.csv",
        "bq_eval_results_table_id": "eval_results.eval_results_table",
        "ragas_metrics": ["faithfulness", "answer_relevancy"],
    }
]


@pytest.mark.parametrize("payload", eval_batch_params)
def test_eval_batch(client, payload):
    response = client.post("/eval_batch", json=payload)
    assert response.status_code == 200
