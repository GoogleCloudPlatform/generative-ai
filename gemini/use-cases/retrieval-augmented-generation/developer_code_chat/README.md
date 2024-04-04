# Overview

This solution showcases the development of an AI-powered learning assistant. This assistant is designed to help programmers or students, learn more about programming languages. The assistant answers users' questions (configured programming languages) using internal documents and Gemini model. It can assist end users with coding tasks, answer questions, and generate code. The solution has been built using the custom RAG approach and Gemini model (Gemini Pro 1.0). It stores the responses in BigQuery. This allows for the caching of more common queries and analytics.

## Please follow the notebook <i>developer_code_chat.ipynb</i>

    - To know more details about the solution design.
    - To experiments with the functionalities created in this solution.

## Folder Structure

1. developer_code_chat/
    - config.ini : Configuration file.
    - developer_code_chat.ipynb: Main demo notebook.
    - embeddings_0.json: Dummy embedding file used as a schema while indexing document.

2. utils/
    - gcs_directory_loader.py : Load directory from GCS Bucket.
    - gcs_file_loader.py : Load files from GCS Bucket.
    - generate_embeddings_utils.py : Embedding Utils.
    - generate_embeddings.py : Generate Embeddings of PDF Documents.
    - intent_routing.py : Contains methods for intent classification and route the request to respective componets.
    - log_response_bq.py : Log response to BigQuery table.
    - vector_search.py : Vector Search implementation using vector store.
    - py_pdf_loader.py : Load PDF Files.
    - py_pdf_parser.py : Modified Langchain PDF Wrappers.
    - qna_vector_search.py : Answer QnA Type Questions using indexed documents.
    - vector_search_utils.py :  Utility functions to create Index and deploy the index to an Endpoint.

3. images/
    - This folder contains images used in the notebook.

4. sample document/
    - This folder includes a PDF file named "Learning_Python.pdf" which can be utilized as a sample document.
    - Store this document in a GCP bucket folder to be used in vector search indexing. In this demo, the PDF file was saved to a GCP folder path, as specified in the setting in the config.ini file using `index_folder_prefix`.
