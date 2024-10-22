from datetime import datetime
import logging
import uuid

from backend.app.dependencies import get_index_manager, get_prompts
from backend.app.models import EvalRequest
from backend.rag.evaluate import LLMEvaluator
from common.utils import download_blob
from datasets import Dataset
from fastapi import APIRouter, Depends
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
import pandas as pd
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

router = APIRouter()
logger = logging.getLogger(__name__)

ragas_metrics_dict = {
    "context_precision": context_precision,
    "answer_relevancy": answer_relevancy,
    "faithfulness": faithfulness,
    "context_relevancy": context_relevancy,
    "context_recall": context_recall,
    "answer_similarity": answer_similarity,
    "answer_correctness": answer_correctness,
}


@router.post("/eval_batch")
def eval_batch(
    eval_batch_request: EvalRequest,
    index_manager=Depends(get_index_manager),
    prompts=Depends(get_prompts),
) -> dict:
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
        eval_df = llm_evaluator.evaluate(react_agent.achat, eval_df)
    else:
        eval_df = llm_evaluator.evaluate(query_engine.aquery, eval_df)

    vertexai_llm = ChatVertexAI(model_name=eval_batch_request.eval_model_name)
    vertexai_embeddings = VertexAIEmbeddings(
        model_name=eval_batch_request.embedding_model_name
    )
    eval_df = eval_df.rename(columns={"retrieved_context": "contexts"})
    eval_df_ds = Dataset.from_pandas(eval_df)
    logger.info(eval_df.columns)

    metrics = [ragas_metrics_dict[m] for m in eval_batch_request.ragas_metrics]
    result = evaluate(
        eval_df_ds, metrics=metrics, llm=vertexai_llm, embeddings=vertexai_embeddings
    )
    ragas_results_df = result.to_pandas()[eval_batch_request.ragas_metrics].fillna(0)

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

    # Uncomment the following line if you want to write results to BigQuery
    # write_results_to_bq(eval_df, table_id=eval_batch_request.bq_eval_results_table_id)
    logging.info(f"EVAL ID: {eval_uuid}")
    return eval_df.to_dict(orient="list")
