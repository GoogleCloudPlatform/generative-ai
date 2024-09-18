from pydantic import BaseModel


class IndexUpdate(BaseModel):
    base_index_name: str
    base_endpoint_name: str
    qa_index_name: str | None
    qa_endpoint_name: str | None
    firestore_db_name: str | None
    firestore_namespace: str | None


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
    eval_model_name: str | None = "gemini-1.5-flash"
    embedding_model_name: str | None = "text-embedding-004"


class EvalRequest(RAGConfig):
    eval_model_name: str = "gemini-1.5-flash"
    embedding_model_name: str | None = "text-embedding-004"
    input_eval_dataset_bucket_uri: str = "test_rag_questions/test_ground_truth.csv"
    bq_eval_results_table_id: str = "eval_results.eval_results_table"
    ragas_metrics: list[str] = ["faithfulness", "answer_relevancy"]
