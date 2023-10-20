# Retrieval Augmented Generation

Using Google Cloud Vertex AI Search, PaLM and LangChain

---

## Vertex AI Search

_**TL;DR**: Large language models (LLMs) are most useful when we combine them with information retrieval tools such as search engines. This can help ensure that generated content is grounded in validated, relevant and up-to-date information._
_This folder demonstrates how to use Google Cloud [Vertex AI Search](https://cloud.google.com/enterprise-search)to achieve this._

### What is Vertex AI Search?

Vertex AI Search lets developers, even those with limited machine learning skills, quickly and easily tap into the power of Google’s foundation models, search expertise, and conversational AI technologies to create enterprise-grade generative AI applications.

Vertex AI Search lets organizations quickly build generative AI powered search engines for customers and employees. The solution is provided within the Google Cloud Console and also via API for integration with enterprise workflows or large language models.

### Using Vertex AI Search

Upload data in the form of documents, web sites or relational databases and then users can retrieve the most relevant document chunks using natural language queries. The API is provided with specific configuration options which are designed to work well in conjunction with LLMs, such as choosing different document chunk types.

### Combining Vertex AI Search with LLMs

As LLMs continue to explode in power and popularity, it has become increasingly clear that tools for information retrieval are an essential part of the stack to unlock many of Gen AI's most valuable use cases.
These retrieval tools allow you to efficiently fetch information from your own data and insert the most relevant extracts directly into LLM prompts. This allows you to ground Generative AI output in data that you know to be relevant, validated and up to date.

Most approaches to retrieval typically require the creation of embeddings from documents and the set up of a vector search engine. Custom solutions such as these are time consuming and complex to create, maintain and host. In contrast, Vertex AI Search is a turnkey search engine which provides Google-quality results as a managed service.
A python [retriever](https://python.langchain.com/docs/modules/data_connection/retrievers.html) class has been provided in `/utils/retriever.py` which allows you to run searches against an Vertex AI Search engine.

## Table of Contents

NOTE: These examples make use of the Vertex AI and Vertex AI Search APIs, which are paid services.

For guidelines on contributing, environment setup and general contextual information on Generative AI and Google tools, please see the main [README](../README.md) in the repository root directory.

```text
retrieval-augmented-generation/     - this directory
├── examples/
    ├── question_answering.ipynb    - examples for question answering over documents
    ├── summarization.ipynb         - examples for document summarization (coming soon)
```
