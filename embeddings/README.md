# Embeddings

<!-- markdownlint-disable MD036 -->

**YouTube Video: What are text embeddings?**

<!-- markdownlint-enable MD036 -->

<!-- markdownlint-disable MD033 -->
<a href="https://www.youtube.com/watch?v=vlcQV4j2kTo&list=PLIivdWyY5sqLvGdVLJZh2EMax97_T-OIB" target="_blank">
  <img src="https://img.youtube.com/vi/vlcQV4j2kTo/maxresdefault.jpg" alt="What are text embeddings?" width="500">
</a>
<!-- markdownlint-enable MD033 -->

This repository explores various techniques and use-cases for embedding in Machine Learning, with a particular focus on text embeddings and their applications.

## Notebooks

- **[vector-search-quickstart.ipynb](vector-search-quickstart.ipynb):** Offers a quickstart guide to setting up and using vector search for finding semantically similar items.
- **[intro-textemb-vectorsearch.ipynb](intro-textemb-vectorsearch.ipynb):** Provides an introduction to text embeddings and their application in building vector search engines.
- **[hybrid-search.ipynb](hybrid-search.ipynb):** Demonstrates building a hybrid search system leveraging both keyword-based search and semantic similarity search with embeddings.
- **[embedding-similarity-visualization.ipynb](embedding-similarity-visualization.ipynb):** Visualizes similarity relationships between embeddings using dimensionality reduction techniques like PCA and t-SNE.
- **[intro_multimodal_embeddings.ipynb](intro_multimodal_embeddings.ipynb):** Introduces the concept of multimodal embeddings, which combine information from different modalities like text and images.
- **[intro_embeddings_tuning.ipynb](intro_embeddings_tuning.ipynb):** Explores techniques for fine-tuning pre-trained embedding models to specific domains and tasks.
- **[task-type-embedding.ipynb](task-type-embedding.ipynb):** Explores techniques for creating embeddings specialized for different tasks.
- **[large-embs-generation-for-vvs.ipynb](large-embs-generation-for-vvs.ipynb):** Demonstrates large-scale embeddings generation for Vertex AI Vector Search.

## Use Cases

### Outlier Detection

- **[bq-vector-search-outlier-detection-audit-logs.ipynb](use-cases/outlier-detection/bq-vector-search-outlier-detection-audit-logs.ipynb):** Shows how to detect and investigate anomalies in audit logs using BigQuery vector search and Cloud Audit logs as an example dataset.
- **[bq-vector-search-outlier-detection-infra-logs.ipynb](use-cases/outlier-detection/bq-vector-search-outlier-detection-infra-logs.ipynb):** Demonstrates building a real-world outlier detection using Gemini and BigQuery vector search. Also shows how to tune hyperparameters and evaluate performance using a public HDFS logs dataset.
