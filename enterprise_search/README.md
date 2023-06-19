# Retrieval Augmented Generation
_Using Google Cloud Enterprise Search, PaLM and Langchain_

---

## Enterprise Search

_**TL;DR**: Large language models (LLMs) are most useful when we combine them with information retrieval tools such as search engines. This can help ensure that generated content is grounded in validated, relevant and up-to-date information. This folder demonstrates how to use Google's [Enterprise Search](https://cloud.google.com/enterprise-search) solution to achieve this._


**What is Enterprise Search?**

[Enterprise Search](https://cloud.google.com/enterprise-search) is an offering from Google Cloud that lets organizations quickly build generative AI powered search engines for customers and employees.  The solution is provided as part of Gen App Builder within Google Cloud and also via API for integration with enterprise workflows or large languagde models.

To use it, upload documents, websites and databases and then users can retrieve the most relevant document chunks using natural language. The API is provided with specific configuration options which are designed to work well in conjunction with LLMs, such as customising the token length of retrieved document chunks.

**Gaining access to Enterprise Search**

Enterprise Search is generally available on an allowlist basis (customers need to be approved for access) as of June 6, 2023. Contact your Google Cloud sales team for access and pricing details. 

**Combining Enterprise Search with LLMs**

As LLMs continue to explode in power and popularity, it has become increasingly clear that tools for information retrieval are an essential part of the stack to unlock many of Gen AI's most valuable use cases.  These retrieval tools allow you to efficiently fetch information from your own data and insert the most relevant extracts directly into LLM prompts. This allows you to ground Generative AI output in data that you know to be relevant, validated and up to date.

Most approaches to retrieval typically require the creation of embeddings from documents and the set up of a vector search engine. Custom solutions such as these are time consuming and complex to create, maintain and host. In contrast, Enterprise Search is a turnkey search engine which provides Google-quality results as a managed service. A python [retriever](https://python.langchain.com/docs/modules/data_connection/retrievers.html) class has been provided in `/utils/retriever.py` which allows you to run searches against an Enterprise Search engine.

Usage is a simple as a few lines of python:
```python
# import libraries
from langchain.llm import VertexAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema import Document

# Use Enterprise Search as a Langchain retriever
class EnterpriseSearchRetriever():
  def __init__(self, project, search_engine):
    …

  def get_relevant_documents(self, query: str) -> List[Document]:
    …

# Configure a Vertex AI LLM and an Enterprise Search engine
llm = VertexAI(**parameters)
retriever = EnterpriseSearchRetriever(gcp_project, search_engine_id)

# Define a summarization prompt
prompt = PromptTemplate("""Use the context docs to answer this query:
Query:
{query}
Context:
{context}
Answer:
 """, input_variables=['query', 'context'])
chain = LLMChain(llm=llm, prompt=prompt)

# Pass search results from a query into the prompt
query = "What do our policy documents say about building regulations?"
search_results = retriever.get_relevant_documents(query)
response = chain.run({"query": query, "context": search_results})
```

## Table of Contents

**Please note that these examples make use of several paid Google APIs:**
* **Vertex AI**
* **Enterprise Search**
* 
- [Enterprise Search/](../enterprise_search)
  - [Utils/](../enterprise-search/utils/)
    - [Enterprise Search Retriever Class](../enterprise-search/utils/retriever.py)
  - [Questioning & Answering](../enterprise-search/question_answering.ipynb)
  - [Document Summarization](../enterprise-search/summarization.ipynb)


For guidelines on contributing, environment setup and general contextual information on Generative AI and Google tools, please see the main [README](../README.md) in the repository root directory.


```
enterprise-search/                  - this directory
├── utils/
    ├── retriever/                  - definition of the retriever class used in the examples
├── question_answering/             - examples for question answering over documents
├── summarization/                  - examples for document summarization
```

