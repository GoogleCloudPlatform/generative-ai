# Generative AI

Welcome to the Google Cloud [Generative AI](https://cloud.google.com/ai/generative-ai) repository.

This repository contains notebooks and content that demonstrate how to use, develop and manage generative AI workflows using [Generative AI](https://cloud.google.com/ai/generative-ai), powered by [Vertex AI](https://cloud.google.com/vertex-ai) on Google Cloud.


## Folder structure
```
generative-ai/
├── language/
    ├── examples/             
        ├── document-qa/             - examples for doc Q&A
        ├── document-summarization/  - examples for doc summarization
        ├── langchain-intro/         - examples for langchain
        ├── prompt-design/           - examples for prompts
        └── tuning/                  - examples of tuning models
└── setup-env/                       - setup instructions
```

## Table of Contents
- [Language/](language/)
  - [Getting Started with Generative AI Studio without code](language/intro_generative_ai_studio.md)
  - [Intro to Vertex AI PaLM API](language/intro_palm_api.ipynb)
  - [Intro to Prompt Design](language/intro_prompt_design.ipynb)
  - [Examples/](language/examples/)
    - [Prompt Design/](language/examples/prompt-design/)
      - [Ideation](language/examples/prompt-design/ideation.ipynb)
      - [Question & Answering](language/examples/prompt-design/question_answering.ipynb)
      - [Text Classifiction](language/examples/prompt-design/text_classification.ipynb)
      - [Text Extraction](language/examples/prompt-design/text_extraction.ipynb)
      - [Text Summarization](language/examples/prompt-design/text_summarization.ipynb)
    - [Reference-architectures/](language/examples/reference-architectures/) \***NEW**\*
      - [Product_description_generator](language/examples/reference-architectures/Product_description_generator.ipynb)
    - [Document Q&A/](language/examples/document-qa/) \***NEW**\*
      - [Question Answering with Large Documents with LangChain](language/examples/document-qa/question_answering_large_documents_langchain.ipynb)
      - [Question Answering with Large Documents (without LangChain)](language/examples/document-qa/question_answering_large_documents.ipynb)
    - [Document Summarization/](language/examples/document-summarization/) \***NEW**\*
<<<<<<< HEAD
      - [Summarization with Large Documents with LangChain](language/examples/document-summarization/summarization_large_documents_langchain.ipynb)
      - [Summarization with Large Documents (without LangChain)](language/examples/document-summarization/summarization_large_documents.ipynb)
    - [LangChain-intro/](language/examples/langchain-intro/) \***NEW**\*
      - [Getting Started with LangChain 🦜️🔗 + Vertex AI PaLM API](language/examples/langchain-intro/intro_langchain_palm_api.ipynb)
    - [Tuning/](language/examples/tuning/)
      - [Tuning a Foundational Model, Deploying, and Making Predictions](language/examples/tuning/getting_started_tuning.ipynb)
      

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

