# Retrieval Augmented Generation

_Using Google Cloud Enterprise Search, PaLM and Langchain_

---

## Generative AI App Builder & Enterprise Search

_**TL;DR**: Large language models (LLMs) are most useful when we combine them with information retrieval tools such as search engines. This can help ensure that generated content is grounded in validated, relevant and up-to-date information._
_This folder demonstrates how to use Google's Generative AI App Builder tools, specifically [Enterprise Search](https://cloud.google.com/enterprise-search) solution to achieve this._

### What is Enterprise Search?

[Enterprise Search](https://cloud.google.com/enterprise-search) is a part of the Generative AI App Builder suite of tools offered by Google Cloud.

Gen AI App Builder lets developers, even those with limited machine learning skills, quickly and easily tap into the power of Google’s foundation models, search expertise, and conversational AI technologies to create enterprise-grade generative AI applications.
Enterprise Search lets organizations quickly build generative AI powered search engines for customers and employees. The solution is provided within the Google Cloud UI and also via API for integration with enterprise workflows or large language models.

### Using Enterprise Search

Enterprise Search is generally available on an allowlist basis (customers need to be approved for access) as of June 6, 2023. Contact your Google Cloud sales team for access and pricing details.

Once you have been granted access, upload data in the form of documents, web sites or relational databases and then users can retrieve the most relevant document chunks using natural language queries. The API is provided with specific configuration options which are designed to work well in conjunction with LLMs, such as choosing different document chunk types.

### Combining Enterprise Search with LLMs

As LLMs continue to explode in power and popularity, it has become increasingly clear that tools for information retrieval are an essential part of the stack to unlock many of Gen AI's most valuable use cases.
These retrieval tools allow you to efficiently fetch information from your own data and insert the most relevant extracts directly into LLM prompts. This allows you to ground Generative AI output in data that you know to be relevant, validated and up to date.

Most approaches to retrieval typically require the creation of embeddings from documents and the set up of a vector search engine. Custom solutions such as these are time consuming and complex to create, maintain and host. In contrast, Enterprise Search is a turnkey search engine which provides Google-quality results as a managed service.
A python [retriever](https://python.langchain.com/docs/modules/data_connection/retrievers.html) class has been provided in `/utils/retriever.py` which allows you to run searches against an Enterprise Search engine.

## Table of Contents

**Please note that these examples make use of the Vertex AI and Generative AI App Builder APIs, which are paid services**

- [Gen App Builder/](/)
  - [Utilities](utils/)
    - [Enterprise Search Retriever Class](utils/retriever.py)
  - [Questioning & Answering](examples/question_answering.ipynb)
  - [Document Summarization](examples/summarization.ipynb)

For guidelines on contributing, environment setup and general contextual information on Generative AI and Google tools, please see the main [README](../README.md) in the repository root directory.

```text
gen-app-builder/                    - this directory
├── utils/
    ├── retriever.py                - definition of the retriever class used in the examples
├── examples/                       - examples for question answering over documents
    ├── question_answering.ipynb    - examples for question answering over documents
    ├── summarization.ipynb         - examples for document summarization (coming soon)
```
