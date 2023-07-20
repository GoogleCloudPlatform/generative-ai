# Generative AI - Language

Welcome to the Google Cloud [Generative AI](https://cloud.google.com/ai/generative-ai/) - Language repository.

## Folder structure

```text
generative-ai/
├── language/
    ├── examples/
        ├── document-qa/             - examples for doc Q&A
        ├── document-summarization/  - examples for doc summarization
        ├── langchain/               - examples for langchain
        ├── prompt-design/           - examples for prompts
        ├── reference-architectures/ - examples of architectures
        └── tuning/                  - examples of tuning models
```

## Table of Contents

- `language/`
  - [Getting Started with Generative AI Studio without code](intro_generative_ai_studio.md)
  - [Intro to Vertex AI PaLM API](intro_palm_api.ipynb)
  - [Intro to Prompt Design](intro_prompt_design.ipynb)
  - [Examples/](examples/)
    - [Prompt Design/](examples/prompt-design/)
      - [Ideation](examples/prompt-design/ideation.ipynb)
      - [Question & Answering](examples/prompt-design/question_answering.ipynb)
      - [Text Classifiction](examples/prompt-design/text_classification.ipynb)
      - [Text Extraction](examples/prompt-design/text_extraction.ipynb)
      - [Text Summarization](examples/prompt-design/text_summarization.ipynb)
    - [Reference-architectures/](examples/reference-architectures/)
      - [Product Description Generator from Image](examples/reference-architectures/product_description_generator_image.ipynb)
      - [Product Description Generator from Product Attributes to Text](examples/reference-architectures/product_description_generator_attributes_to_text.ipynb) \***NEW**\*
      - [GroceryBot: a sample grocery and recipe assistant - RAG + ReAct](examples/reference-architectures/grocerybot_assistant.ipynb) \***NEW**\*
    - [Document Q&A/](examples/document-qa/)
      - [Question Answering with Large Documents with LangChain](examples/document-qa/question_answering_large_documents_langchain.ipynb)
      - [Question Answering with Large Documents with LangChain and Vertex AI Matching Engine](examples/document-qa/question_answering_documents_langchain_matching_engine.ipynb) \***NEW**\*
      - [Question Answering with Large Documents (without LangChain)](examples/document-qa/question_answering_large_documents.ipynb)
    - [Document Summarization/](examples/document-summarization/)
      - [Summarization with Large Documents with LangChain](examples/document-summarization/summarization_large_documents_langchain.ipynb)
      - [Summarization with Large Documents (without LangChain)](examples/document-summarization/summarization_large_documents.ipynb)
    - [LangChain-intro/](examples/langchain-intro/)
      - [Getting Started with LangChain 🦜️🔗 + Vertex AI PaLM API](examples/langchain-intro/intro_langchain_palm_api.ipynb)
    - [Tuning/](examples/tuning/)
      - [Tuning a Foundational Model, Deploying, and Making Predictions](examples/tuning/getting_started_tuning.ipynb)
