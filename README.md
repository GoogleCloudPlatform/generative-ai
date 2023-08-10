# Generative AI

Welcome to the Google Cloud [Generative AI](https://cloud.google.com/ai/generative-ai) repository.

This repository contains notebooks and content that demonstrate how to use, develop and manage generative AI workflows using [Generative AI](https://cloud.google.com/ai/generative-ai), powered by [Vertex AI](https://cloud.google.com/vertex-ai) and [Generative AI App Builder](https://cloud.google.com/generative-ai-app-builder) on Google Cloud.

## Table of Contents  
<pre>  
generative-ai/
├── <a href="CONTRIBUTING.md">CONTRIBUTING.md</a>
├── <a href="RESOURCES.md">RESOURCES.md</a>
├── <a href="gen-app-builder">gen-app-builder/</a>
│   ├── <a href="gen-app-builder/chat-app">chat-app/</a>
│   ├── <a href="gen-app-builder/data-store-status-checker">data-store-status-checker/</a>
│   │   └── <a href="gen-app-builder/data-store-status-checker/data_store_checker.ipynb">[Notebook] Gen App Builder Data Store Status Checker</a>
│   ├── <a href="gen-app-builder/retrieval-augmented-generation">retrieval-augmented-generation/</a>
│   │   └── <a href="gen-app-builder/retrieval-augmented-generation/examples">examples/</a>
│   │       └── <a href="gen-app-builder/retrieval-augmented-generation/examples/question_answering.ipynb">[Notebook] Question Answering with Generative Models on Vertex AI</a>
│   └── <a href="gen-app-builder/search-web-app">search-web-app/</a>
├── <a href="language">language/</a>
│   ├── <a href="language/hello-world">hello-world/</a>
│   │   ├── <a href="language/hello-world/intro_generative_ai_studio.md">intro_generative_ai_studio.md</a>
│   │   └── <a href="language/hello-world/intro_palm_api.ipynb">[Notebook] Getting Started with the Vertex AI PaLM API & Python SDK</a>
│   ├── <a href="language/prompts">prompts/</a>
│   │   ├── <a href="language/prompts/examples">examples/</a>
│   │   │   ├── <a href="language/prompts/examples/ideation.ipynb">[Notebook] Ideation with Generative Models on Vertex AI</a>
│   │   │   ├── <a href="language/prompts/examples/question_answering.ipynb">[Notebook] Question Answering with Generative Models on Vertex AI</a>
│   │   │   ├── <a href="language/prompts/examples/text_classification.ipynb">[Notebook] Text Classification with Generative Models on Vertex AI</a>
│   │   │   ├── <a href="language/prompts/examples/text_extraction.ipynb">[Notebook] Text Extraction with Generative Models on Vertex AI</a>
│   │   │   └── <a href="language/prompts/examples/text_summarization.ipynb">[Notebook] Text Summarization with Generative Models on Vertex AI</a>
│   │   └── <a href="language/prompts/intro_prompt_design.ipynb">[Notebook] Prompt Design - Best Practices</a>
│   ├── <a href="language/third-party">third-party/</a>
│   │   └── <a href="language/third-party/langchain">langchain/</a>
│   │       └── <a href="language/third-party/langchain/intro_langchain_palm_api.ipynb">[Notebook] Getting Started with LangChain 🦜️🔗 + Vertex AI PaLM API</a>
│   ├── <a href="language/tuning">tuning/</a>
│   │   └── <a href="language/tuning/getting_started_tuning.ipynb">[Notebook] Tuning and deploy a foundation model</a>
│   └── <a href="language/use-cases">use-cases/</a>
│       ├── <a href="language/use-cases/chatbots">chatbots/</a>
│       │   └── <a href="language/use-cases/chatbots/grocerybot_assistant.ipynb">[Notebook] GroceryBot, a sample grocery and recipe assistant - RAG + ReAct</a>
│       ├── <a href="language/use-cases/description-generation">description-generation/</a>
│       │   ├── <a href="language/use-cases/description-generation/product_description_generator_attributes_to_text.ipynb">[Notebook] DescriptionGen: SEO-optimized product decription generation for retail using LangChain 🦜🔗</a>
│       │   └── <a href="language/use-cases/description-generation/product_description_generator_image.ipynb">[Notebook] Product Description Generator From Image</a>
│       ├── <a href="language/use-cases/document-qa">document-qa/</a>
│       │   ├── <a href="language/use-cases/document-qa/question_answering_documents_langchain_matching_engine.ipynb">[Notebook] Question Answering with Documents using LangChain 🦜️🔗 and Vertex AI Matching Engine</a>
│       │   ├── <a href="language/use-cases/document-qa/question_answering_large_documents.ipynb">[Notebook] Question Answering with Large Documents</a>
│       │   └── <a href="language/use-cases/document-qa/question_answering_large_documents_langchain.ipynb">[Notebook] Question Answering with Large Documents using LangChain 🦜🔗</a>
│       └── <a href="language/use-cases/document-summarization">document-summarization/</a>
│           ├── <a href="language/use-cases/document-summarization/summarization_large_documents.ipynb">[Notebook] Text Summarization of Large Documents</a>
│           └── <a href="language/use-cases/document-summarization/summarization_large_documents_langchain.ipynb">[Notebook] Text Summarization of Large Documents using LangChain 🦜🔗</a>
└── <a href="setup-env">setup-env/</a>
</pre>

## Setting up your Google Cloud project

You will need a Google Cloud project to use this project.

1. [Select or create a Google Cloud project](https://console.cloud.google.com/cloud-resource-manager). When you first create an account, you get a $300 free credit towards your compute/storage costs.

2. [Make sure that billing is enabled for your project](https://cloud.google.com/billing/docs/how-to/modify-project).

3. [Enable the Vertex AI API](https://console.cloud.google.com/flows/enableapi?apiid=aiplatform.googleapis.com).

## Setting up your Python or Jupyter environment

Please see the README in the [setup-env](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/setup-env) folder for information on using Colab notebooks and Vertex AI Workbench.

## Google Generative AI Resources

Check out a list of [Google Generative AI Resources](RESOURCES.md) like official product pages, documentation, videos, courses and more.

## Contributing

Contributions welcome! See the [Contributing Guide](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/CONTRIBUTING.md).

## Getting help

Please use the [issues page](https://github.com/GoogleCloudPlatform/generative-ai/issues) to provide feedback or submit a bug report.

## Disclaimer

This repository itself is not an officially supported Google product. The code in this repository is for demonstrative purposes only.
