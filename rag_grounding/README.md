# RAG and Grounding

This directory provides a curated list of notebooks that explore Retrieval
Augmented Generation (RAG), grounding techniques, knowledge bases, grounded
generation, and related topics like vector search and semantic search.

All of these links are notebooks or other examples in this repository, but are
indexed here for your convenience.

## What is RAG and Grounding?

![Animated GIF showing "what is grounding"](./img/what-is-grounding.gif)

- Ungrounded generation relies on the LLM training data alone and is prone to
  hallucinations when it doesn't have all the right facts
- **Grounding** a LLM with relevant facts provides fresh and potentially private
  data to the model as part of it's input or prompt
- **RAG** is a technique which retrievs relevant facts, often via search, and
  provides them to the LLM

Using RAG and Grounding to improve generations and reduce hallucinations is
becoming commonplace. Doing so well and generating extremely high quality
results which are entirely grounded on the most relevant facts, potentially from
a very large corpus of information and at high scale - is an art. Vertex
provides a platform of tools and APIs which help you build and maintain a great
search engine and RAG application, and the evaluations needed to hill climb
"quality".

## Measuring RAG/Grounding Quality

See
[this blog post: How to evaluate generated answers from RAG at scale on Vertex AI](https://medium.com/google-cloud/vqa-3-how-to-evaluate-generated-answers-from-rag-at-scale-on-vertex-ai-70bc397cb33d)
for a walkthrough.

- **[evaluate_rag_gen_ai_evaluation_service_sdk.ipynb](../gemini/evaluation/evaluate_rag_gen_ai_evaluation_service_sdk.ipynb)**:
  Evaluates RAG systems using the Gen AI Evaluation Service SDK.
- **[ragas_with_gemini.ipynb](../use-cases/retrieval-augmented-generation/rag-evaluation/ragas_with_gemini.ipynb)**:
  Use Case - using Ragas with Gemini for Eval.
- **[deepeval_with_gemini.ipynb](../use-cases/retrieval-augmented-generation/rag-evaluation/deepeval_with_gemini.ipynb)**:
  Use Case - using Deepeval with Gemini for Eval.

## Out of the Box RAG/Grounding

- **[Vertex AI Search - sample Web App](../search/web-app/)**: Take a look at
  this sample web app using Vertex AI Search, which is a flexible and easy to
  use "out of the box" solution for search & RAG/Grounding.
- **[bulk_question_answering.ipynb](../search/bulk-question-answering/bulk_question_answering.ipynb)**:
  Answers multiple questions using a search system
- **[contract_analysis.ipynb](../search/retrieval-augmented-generation/examples/contract_analysis.ipynb)**,
  **[question_answering.ipynb](../search/retrieval-augmented-generation/examples/question_answering.ipynb)**,
  **[rag_google_documentation.ipynb](../search/retrieval-augmented-generation/examples/rag_google_documentation.ipynb)**:
  Showcase specific RAG use cases
- **[search_data_blending_with_gemini_summarization.ipynb](../search/search_data_blending_with_gemini_summarization.ipynb)**:
  Demonstrates calling a search app that blends information from multiple stores
  (GCS, BQ, Website) and summarizes search snippets and responses using the
  Gemini Pro model.
- **[vertexai_search_options.ipynb](../search/vertexai-search-options/vertexai_search_options.ipynb)**:
  Shows how to use Vertex AI Search in conjunction with the Gemini Pro model to
  retrieve and summarize data across multiple data stores within Google Cloud
  Platform (GCP). It highlights how the Gemini Pro model is able to formulate a
  summary of user-specific prompts based on the retrieved snippets and citations
  from Vertex AI Search.

## Build your own RAG/Grounding

We have several notebooks and examples for specific use cases or types of data
which may require a custom RAG and Grounding. We have many products which can be
used to build a RAG/Grounding pipeline of your own, or which you can add to an
existing RAG and Grounding solution.

- [Vertex AI APIs for building search and RAG](https://cloud.google.com/generative-ai-app-builder/docs/builder-apis)
  has a list of several APIs you can use in isolation or in combination
- [LlamaIndex on Vertex](https://cloud.google.com/vertex-ai/generative-ai/docs/rag-overview)
  allows you to assemble a RAG search using popular OSS framework and components
  from Google or Open Source
- [This end-to-end DIY RAG example in a notebook](https://github.com/GoogleCloudPlatform/applied-ai-engineering-samples/blob/main/genai-on-vertex-ai/retrieval_augmented_generation/diy_rag_with_vertexai_apis/build_grounded_rag_app_with_vertex.ipynb)
  written in LangChain and using some of these APIs
- The Google Cloud Architecture Center has reference architectures on
  [building a RAG infrastructure with GKE](https://cloud.google.com/architecture/rag-capable-gen-ai-app-using-gke)
  or
  [using alloydb and a few Vertex services](https://cloud.google.com/architecture/rag-capable-gen-ai-app-using-vertex-ai)

### Search

Vertex AI Search is an end to end Search engine which has it's own grounded
generation and RAG built in.

Vertex AI Vector Search is a extremely perfomant Vector Database which powers
Vertex AI Search. Other database like AlloyDB and BigQuery also have vector
searches, each with different performance characterstics and retrieval
perormance.

### Embeddings

- **[intro_Vertex_AI_embeddings.ipynb](../gemini/qa-ops/intro_Vertex_AI_embeddings.ipynb)**:
  Introduces Vertex AI embeddings.
- **[hybrid-search.ipynb](../embeddings/hybrid-search.ipynb)**: Explores
  combining different search techniques, potentially including vector search and
  keyword-based search.
- **[intro-textemb-vectorsearch.ipynb](../embeddings/intro-textemb-vectorsearch.ipynb)**:
  Introduces text embeddings and vector search.
- **[vector-search-quickstart.ipynb](../embeddings/vector-search-quickstart.ipynb)**:
  Quick start guide for implementing vector search.
- **[bq-vector-search-log-outlier-detection.ipynb](../embeddings/use-cases/outlier-detection/bq-vector-search-log-outlier-detection.ipynb)**:
  Demonstrates using vector search with BigQuery logs to identify outliers.

### Gemini

- **[intro-grounding-gemini.ipynb](../gemini/grounding/intro-grounding-gemini.ipynb)**:
  Introduces grounding in the context of Gemini.
- **[building_DIY_multimodal_qa_system_with_mRAG.ipynb](../gemini/qa-ops/building_DIY_multimodal_qa_system_with_mRAG.ipynb)**:
  Builds a custom multimodal question-answering system using mRAG.
- **[code_retrieval_augmented_generation.ipynb](../language/code/code_retrieval_augmented_generation.ipynb)**:
  Demonstrates using code retrieval to improve code generation.
- **[intro-grounding.ipynb](../language/grounding/intro-grounding.ipynb)**:
  Introduction to grounding in natural language processing
- **[langchain_bigquery_data_loader.ipynb](../language/orchestration/langchain/langchain_bigquery_data_loader.ipynb)**:
  Uses LangChain to load data from BigQuery for RAG
- **[question_answering_documents.ipynb](../language/use-cases/document-qa/question_answering_documents.ipynb)**,
  **[question_answering_documents_langchain.ipynb](../language/use-cases/document-qa/question_answering_documents_langchain.ipynb)**,
  **[question_answering_documents_langchain_matching_engine.ipynb](../language/use-cases/document-qa/question_answering_documents_langchain_matching_engine.ipynb)**:
  Focus on question answering over documents
- **[summarization_large_documents.ipynb](../language/use-cases/document-summarization/summarization_large_documents.ipynb)**,
  **[summarization_large_documents_langchain.ipynb](../language/use-cases/document-summarization/summarization_large_documents_langchain.ipynb)**:
  Demonstrate summarizing large documents.

### Open Models

- **[cloud_run_ollama_gemma2_rag_qa.ipynb](../open-models/serving/cloud_run_ollama_gemma2_rag_qa.ipynb)**:
  Sets up a RAG-based question-answering system using Ollama and Gemma2 on Cloud
  Run

## Agents on top of RAG

- **[tutorial_vertex_ai_search_rag_agent.ipynb](../gemini/reasoning-engine/tutorial_vertex_ai_search_rag_agent.ipynb)**:
  Tutorial for building RAG agents using Vertex AI Search
- **[tutorial_alloydb_rag_agent.ipynb](../gemini/reasoning-engine/tutorial_alloydb_rag_agent.ipynb)**:
  Tutorial for building RAG agents using AlloyDB
- **[tutorial_cloud_sql_pg_rag_agent.ipynb](../gemini/reasoning-engine/tutorial_cloud_sql_pg_rag_agent.ipynb)**:
  Tutorial for building RAG agents using Cloud SQL (PostgreSQL)

## Use Cases

These notebooks offer a valuable resource to understand and implement RAG and
grounding techniques in various applications. Feel free to dive into the
notebooks that pique your interest and start building your own RAG-powered
solutions.

- Examples of RAG in different domains
  - **[Document_QnA_using_gemini_and_vector_search.ipynb](../use-cases/retrieval-augmented-generation/Document_QnA_using_gemini_and_vector_search.ipynb)**
  - **[NLP2SQL_using_dynamic_RAG.ipynb](../use-cases/retrieval-augmented-generation/NLP2SQL_using_dynamic_RAG.ipynb)**
  - **[RAG_Based_on_Sensitive_Data_Protection_using_Faker.ipynb](../use-cases/retrieval-augmented-generation/RAG_Based_on_Sensitive_Data_Protection_using_Faker.ipynb)**
  - **[code_rag.ipynb](../use-cases/retrieval-augmented-generation/code_rag.ipynb)**
  - **[intra_knowledge_qna.ipynb](../use-cases/retrieval-augmented-generation/intra_knowledge_qna.ipynb)**
  - **[intro_multimodal_rag.ipynb](../use-cases/retrieval-augmented-generation/intro_multimodal_rag.ipynb)**
  - **[llamaindex_rag.ipynb](../use-cases/retrieval-augmented-generation/llamaindex_rag.ipynb)**
  - **[multimodal_rag_langchain.ipynb](../use-cases/retrieval-augmented-generation/multimodal_rag_langchain.ipynb)**
  - **[small_to_big_rag.ipynb](../use-cases/retrieval-augmented-generation/small_to_big_rag/small_to_big_rag.ipynb)**
- Build RAG systems using BigQuery
  - **[rag_qna_with_bq_and_featurestore.ipynb](../use-cases/retrieval-augmented-generation/rag_qna_with_bq_and_featurestore.ipynb)**
  - **[rag_vector_embedding_in_bigquery.ipynb](../use-cases/retrieval-augmented-generation/rag_vector_embedding_in_bigquery.ipynb)**
