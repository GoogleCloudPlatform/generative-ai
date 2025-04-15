# What is Vertex AI Search?

Vertex AI Search (VAIS) is a fully-managed platform, powered by large
language models, that lets you build AI-enabled search and recommendation
experiences for your public or private sites or mobile applications
VAIS can handle a diverse set of data sources including structured,
unstructured, and site data, as well as data from third-party applications
such as Jira, Salesforce, and Confluence.
VAIS also has built-in integration with LLMs which enables you to provide
answers to complex questions, grounded in your data

## Sample Notebooks

This folder contains a series of notebooks to demonstrate how different
functionalities within Vertex AI Search can be used
We aim to keep these notebooks broader than a single API call and smaller
than a fully fledged application.
The notebooks are expected to serve as building blocks which can be
combined to achieve higher levels goals (e.g. ingest unstructured documents
with metadata and generate accurate answers based on that)
We will try to use REST APIs which will hopefully make the codes easier to
understand without a need to read through documentations of different object
types. For production use, many customer prefer Client libraries. Please consult

The [official documentation](https://cloud.google.com/generative-ai-app-builder/docs/apis) for alternative ways of achieving the same goals.

## List of Notebooks

1. [Ingestion of Unstructured Documents with Metadata in Vertex AI Search]
   (./ingesting_unstructured_documents_with_metadata.ipynb)

2. [Parsing and Chunking in Vertex AI Search: Featuring BYO Capabilities]
   (./parsing_and_chunking_with_BYO.ipynb)

3. [Defining custom attributes based on URL patterns in Vertex AI Search
   Site Datastores](./custom_attributes_by_url_pattern.ipynb)

4. [Query-Level Boosting, Filtering, and Facets for Vertex AI Search Site
   Datastores](./query_level_boosting_filtering_and_facets.ipynb)

5. [Inline Ingestion of Documents into Vertex AI Search]
   (./inline_ingestion_of_documents.ipynb)

6. [Event-based Triggering of Manual Recrawl for Vertex AI Search Advanced
   Site Datastores](./manual_recrawl_urls_with_trigger.ipynb)

7. [Recording Real-Time User Events in Vertex AI Search Datastores]
   (./record_user_events.ipynb)
