# Generative AI - Vertex AI Search

Welcome to the Google Cloud [Generative AI](https://cloud.google.com/ai/generative-ai/) - Vertex AI Search repository.

Google Cloud Vertex AI is Powering the Future of Search. Google Cloud Vertex AI offers a comprehensive suite of tools and services to address the above search patterns.

Building and managing RAG systems can be complex and can be quite nuanced. Developers need to develop and maintain several RAG building blocks like data connectors, data processing, chunking, annotating, vectorization with embeddings, indexing, query rewriting, retrieval, reranking, along with LLM-powered summarization. Designing, building and maintaining this pipeline can be time and resource intensive. Being able to scale each of the components to handle bursty search traffic and coping with a large corpus of varied and frequently updated data can be challenging. Speaking of scale, as the queries per second ramp up many vector databases degrade both recall and latency metrics.

[Vertex AI Search](https://cloud.google.com/generative-ai-app-builder/docs/enterprise-search-introduction) leverages decades of Google's expertise in information retrieval and brings together the power of deep information retrieval, state-of-the-art natural language processing, and the latest in large language model (LLM) processing to understand user intent and return the most relevant results for the user. No matter where you are in the development journey, Vertex AI Search provides several options to bring your enterprise truth to life from out-of-the-box (OOTB) to DIY RAG.

## Why Vertex AI Search Out-of-the-box

The out-of-the-box solution can bring Google-Quality search to build end-to-end state-of-the-art semantic and hybrid search applications.

- It has in-built connectors to several data sources: (Cloud Storage, BigQuery, sites, Confluence, Jira, Salesforce, Slack and many more).
- It has a state of the art document layout parser capable of keeping chunks of data organized across pages, containing embedded tables, annotating embedded images, and can track heading ancestry as metadata for each chunk.
- It uses "hybrid search" - a combination of keyword (sparse) and LLM (dense) based embeddings to be able to handle any user query.Sparse vectors tend to directly map words to numbers and dense vectors are designed to better represent the meaning of a piece of text.
- It leverages advanced [neural matching](https://blog.google/products/search/improving-search-next-20-years/) between user queries and document snippets to retrieve highly relevant and ranked results for the user. Neural matching allows a retrieval engine to learn the relationships between intention of a query and highly relevant documents, allowing Search to recognize the context of a query instead of the simple similarity search.
- It provides users with LLM powered summaries with citations and is designed to scale to your search traffic. Vertex AI Search supports custom LLM instruction templates, making it easy to create powerful engaging search experiences with minimal effort.
- Anyone can build a RAG search engine grounded on their own data in minutes with our console, developers can also use our API to programmatically build and test the OOTB agent.

⭐ Explore [Part 1 of this notebook example](vertexai-search-options/vertexai_search_options.ipynb) to see Vertex AI Agent Builder SDK in action.

## For greater customization

Vertex AI Search SDK further allows developers to integrate Vertex AI Search with open-source LLMs or other custom components, tailoring the search pipeline to their specific needs. As mentioned above, building end-to-end RAG solutions can be complex, developers might want to rely on Vertex AI Search as a grounding source for search results retrieval and ranking, and leverage custom LLM for the guided summary. Vertex AI Search also provides grounding in Google Search.

⭐ Find an example for using Vertex AI Search to Ground Responses for Gemini mode in [Part 2 of this example notebook](vertexai-search-options/vertexai_search_options.ipynb).

Developers might already be building their LLM application with frameworks like Langchain/ LLamaIndex. Vertex AI Search has native integration with LangChain and other frameworks, allowing developers to retrieve search results and/or grounded generation. Vertex AI Search can also be linked as an available tool in Vertex AI Gemini SDK. Likewise Vertex AI Search can be a retrieval source for the new [Grounded Generation API](https://cloud.google.com/generative-ai-app-builder/docs/grounded-gen) powered with Gemini "high fidelity mode" which is fine-tuned for grounded generation.

⭐ [Part 3 of this notebook example](vertexai-search-options/vertexai_search_options.ipynb) for leveraging Vertex AI Search from LangChain.

Vertex AI provides the essential building blocks for developers who want to construct their own end-to-end RAG solutions with full flexibility. These include APIs for document parsing, chunking, LLM text and multimodal vector embeddings, versatile vector database options (Vertex AI Vector Search, AlloyDB, BigQuery Vector DB), reranking APIs, and grounding checks.

- Learn more about the Build your own RAG workflow with DIY APIs [here](https://cloud.google.com/generative-ai-app-builder/docs/builder-apis#build-rag).
- Find [this example repository](https://github.com/GoogleCloudPlatform/applied-ai-engineering-samples/blob/main/genai-on-vertex-ai/retrieval_augmented_generation/diy_rag_with_vertexai_apis/build_grounded_rag_app_with_vertex.ipynb) for bringing your DIY end-to-end RAG workflows to live with Vertex AI DIY APIs.

It is also worth noting that [Gemini 1.5 Pro](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models#gemini-1.5-pro) available on Vertex AI supports a 2M token input context window, around 2000 pages worth of context, while maintaining [state-of-the-art reasoning capabilities](https://deepmind.google/technologies/gemini/pro/?_gl=1*128a4ox*_up*MQ..*_ga*MTgzMDgwODIxNC4xNzE5OTU2NjIw*_ga_LS8HVHCNQ0*MTcxOTk1NjYyMC4xLjAuMTcxOTk1NjYyMC4wLjAuMA..). Recently Google DeepMind and University of Michigan published a comprehensive research on [RAG or Long Context window](https://arxiv.org/html/2407.16833v1). Gemini 1.5 Pro can reason with user input query, available Prompt System Instructions, the given context and respond to user queries. With the long context window clubbed with multimodal reasoning, caching ability, developers can quickly start with Gemini 1.5 Pro to quickly test and prototype their semantic information retrieval use case. Once you scale up your source data or usage profile, you will need RAG, possibly in concert with long context window.

![Building Search Applications with Vertex AI](vertexai-search-options/search_options.png)

Based on where Developers are in their journey, their orchestration framework of choice, they can select Vertex AI Search out-of-the-box capabilities or customize their search solutions with Vertex AI Search Retrievers or use the Vertex AI DIY APIs to build the end-to-end RAG application.

Understanding the appetite your organization has towards building, maintaining and scaling RAG applications can also help guide a particular solution path.

## Table of Contents

<!-- markdownlint-disable MD033 -->
<pre>
search/
└── <a href="bulk-question-answering">bulk-question-answering/</a>
|    └──  <a href="bulk-question-answering/bulk_question_answering.ipynb">[Notebook] question/ answering from csv using Vertex AI Search </a>
└── <a href="cloud-function">cloud-function/</a>
|    └──  <a href="cloud-function">[Demo] Access Vertex AI Search from Google Cloud Function </a>
└── <a href="custom-embeddings">custom-embeddings/</a>
|    └──  <a href="custom-embeddings/custom_embeddings.ipynb">[Notebook] Custom Embeddings with Vertex AI Search </a>
├── <a href="retrieval-augmented-generation">retrieval-augmented-generation/</a>
│    └──  <a href="retrieval-augmented-generation/examples/question_answering.ipynb">[Notebook] Question Answering Over Documents with Vertex AI Search and LangChain 🦜🔗</a>
└── <a href="vertexai-search-options">vertexai-search-options/</a>
│    └──  <a href="vertexai-search-options/vertexai_search_options.ipynb">[Notebook] Various ways to build with Vertex AI Search </a>
└── <a href="web-app">web-app/</a>
    └──  <a href="web-app">[Demo] Vertex AI Search Web Application</a>
</pre>
