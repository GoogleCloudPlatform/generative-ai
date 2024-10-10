import logging

from backend.app.dependencies import get_index_manager, get_prompts
from backend.app.models import RAGRequest
from datasets import Dataset
from fastapi import APIRouter, Depends
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
import pandas as pd
from ragas import evaluate
from ragas.metrics import answer_relevancy, context_relevancy, faithfulness

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query_rag")
async def query_rag(
    rag_request: RAGRequest,
    index_manager=Depends(get_index_manager),
    prompts=Depends(get_prompts),
) -> dict:
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
        retrieved_contexts = [r.node.text for r in response.source_nodes]
        eval_df = pd.DataFrame(
            {
                "question": rag_request.query,
                "answer": [response.response],
                "contexts": [retrieved_contexts],
            }
        )
        eval_df_ds = Dataset.from_pandas(eval_df)

        vertexai_llm = ChatVertexAI(model_name=rag_request.eval_model_name)
        vertexai_embeddings = VertexAIEmbeddings(
            model_name=rag_request.embedding_model_name
        )

        metrics = [answer_relevancy, faithfulness, context_relevancy]
        result = evaluate(
            eval_df_ds,
            metrics=metrics,
            llm=vertexai_llm,
            embeddings=vertexai_embeddings,
        )
        result_dict = (
            result.to_pandas()[
                ["answer_relevancy", "faithfulness", "context_relevancy"]
            ]
            .fillna(0)
            .iloc[0]
            .to_dict()
        )
        retrieved_context_dict = {"retrieved_chunks": response.source_nodes}
        logger.info(result_dict)
        return {"response": response.response} | result_dict | retrieved_context_dict
    else:
        return {"response": response.response}
