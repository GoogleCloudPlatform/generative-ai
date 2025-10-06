# Embeddings

This repository explores various techniques and use-cases for embedding in Machine Learning, with a particular focus on text embeddings and their applications.

## Notebooks

- [Import from BigQuery into Vector Search](bigquery-import.ipynb): Learn how to import vector embedding data from a BigQuery data source into a Vector Search index.
- [Use Gemini and OSS Text-Embedding Models Against Your BigQuery Data](bigquery_ml_gemini_and_oss_text_embedding.ipynb): Learn how to generate text embeddings using BigQuery in conjunction with both Gemini and OSS text embedding models.
- [Vertex AI Vector Search Quickstart](vector-search-quickstart.ipynb): A quickstart guide to setting up and using Vertex AI Vector Search.
- [Introduction to Text Embeddings and Vector Search](intro-textemb-vectorsearch.ipynb): Provides an introduction to text embeddings and their application in building vector search engines.
- [Hybrid Search](hybrid-search.ipynb): Demonstrates building a hybrid search system leveraging both keyword-based search and semantic similarity search with embeddings.
- [Embedding Similarity Visualization](embedding-similarity-visualization.ipynb): Visualizes similarity relationships between embeddings using dimensionality reduction techniques like PCA and t-SNE.
- [Introduction to Multimodal Embeddings](intro_multimodal_embeddings.ipynb): Introduces the concept of multimodal embeddings, which combine information from different modalities like text and images.
- [Introduction to Embeddings Tuning](intro_embeddings_tuning.ipynb): Explores techniques for fine-tuning pre-trained embedding models to specific domains and tasks.
- [Task-specific Embeddings](task-type-embedding.ipynb): Explores techniques for creating embeddings specialized for different tasks.
- [Large-scale Embeddings Generation for Vector Search](large-embs-generation-for-vvs.ipynb): Demonstrates large-scale embeddings generation for Vertex AI Vector Search.

## Use Cases

### Outlier Detection

- [Outlier Detection with BigQuery Vector Search (Audit Logs)](use-cases/outlier-detection/bq-vector-search-outlier-detection-audit-logs.ipynb): Shows how to detect and investigate anomalies in audit logs using BigQuery vector search and Cloud Audit logs as an example dataset.
- [Outlier Detection with BigQuery Vector Search (Infra Logs)](use-cases/outlier-detection/bq-vector-search-outlier-detection-infra-logs.ipynb): Demonstrates building a real-world outlier detection using Gemini and BigQuery vector search.
