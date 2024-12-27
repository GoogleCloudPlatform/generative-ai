# Open Models

This repository contains examples for deploying and fine-tuning open source models with Vertex AI.

## Notebooks

### Serving

- [serving/cloud_run_ollama_gemma2_rag_qa.ipynb](./serving/cloud_run_ollama_gemma2_rag_qa.ipynb) - This notebooks provides steps and code to deploy an open source RAG pipeline to Cloud Run using Ollama and the Gemma 2 model.
- [serving/vertex_ai_text_generation_inference_gemma.ipynb](./serving/vertex_ai_text_generation_inference_gemma.ipynb) - This notebooks provides steps and code to deploy Google Gemma with the Hugging Face DLC for Text Generation Inference (TGI) on Vertex AI.
- [serving/vertex_ai_pytorch_inference_paligemma_with_custom_handler.ipynb](./serving/vertex_ai_pytorch_inference_paligemma_with_custom_handler.ipynb) - This notebooks provides steps and code to deploy Google PaliGemma with the Hugging Face Python Inference DLC using a custom handler on Vertex AI.

### Fine-tuning

- [fine-tuning/vertex_ai_trl_fine_tuning_gemma.ipynb](./fine-tuning/vertex_ai_trl_fine_tuning_gemma.ipynb) - This notebooks provides steps and code to fine-tune Google Gemma with TRL via the Hugging Face PyTorch DLC for Training on Vertex AI.

### Use cases

- [use-cases/guess_app.ipynb](./use-cases/guess_app.ipynb) - This notebook shows how to build a "Guess Who or What" app using FLUX and Gemini.
