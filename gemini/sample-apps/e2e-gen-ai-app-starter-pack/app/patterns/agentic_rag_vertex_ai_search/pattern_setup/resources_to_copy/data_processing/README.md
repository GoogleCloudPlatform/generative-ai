# Ingestion Pipeline

This pipeline is designed to automate the ingestion of data into Vertex AI Search (Agent Builder Search) for use in Retrieval Augmented Generation (RAG) applications. It handles the complete workflow of loading documents, chunking them into appropriate segments, generating embeddings using Vertex AI Embeddings, and importing the processed data into your Vertex AI Search datastore.

The pipeline can be triggered as a one-time execution for initial data loading or scheduled to run periodically using a cron schedule for keeping your search index up-to-date. It leverages Vertex AI Pipelines for orchestration & monitoring.

For detailed step-by-step instructions on setting up and running this pipeline, please refer to the [Agentic RAG with Vertex AI Search Pattern Guide](../app/patterns/agentic_rag_vertex_ai_search/README.md).
