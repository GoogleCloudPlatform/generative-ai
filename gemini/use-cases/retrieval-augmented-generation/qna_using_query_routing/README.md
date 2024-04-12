# Overview

This notebook showcases the use of query routing techniques to improve retrieval performance in an AI-powered learning assistant for a computer training institute. This assistant is designed to use LLM to classify the intent of the user query, which in turn determines the appropriate source(s) to answer the query. The solution has been built using the custom RAG approach and Gemini model (Gemini Pro 1.0).

## Please follow the notebook <i>qna_using_query_routing.ipynb</i>

    - To know more details about the solution design.
    - To experiment with the functionalities created in this solution.

## Folder Structure

1. qna_using_query_routing/
    - config.ini : Configuration file.
    - qna_using_query_routing.ipynb: Main demo notebook.

2. utils/
    - intent_routing.py : Contains methods for intent classification and route the request to respective componets.
    - qna_vector_search.py : Answer QnA Type Questions using indexed documents.
    - qna_using_query_routing_utils.py : Contains other utility functions.

3. images/
    - This folder contains images used in the notebook.
