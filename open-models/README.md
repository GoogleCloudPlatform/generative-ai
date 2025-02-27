# Open Models

This repository contains examples for deploying and fine-tuning open source models with Vertex AI.

## Notebooks

### Serving

- [serving/vertex_ai_text_generation_inference_gemma.ipynb](./serving/vertex_ai_text_generation_inference_gemma.ipynb) - This notebooks provides steps and code to deploy Google Gemma with the Hugging Face DLC for Text Generation Inference (TGI) on Vertex AI.
- [serving/vertex_ai_pytorch_inference_paligemma_with_custom_handler.ipynb](./serving/vertex_ai_pytorch_inference_paligemma_with_custom_handler.ipynb) - This notebooks provides steps and code to deploy Google PaliGemma with the Hugging Face Python Inference DLC using a custom handler on Vertex AI.
- [serving/vertex_ai_tgi_gemma_multi_lora_adapters_deployment.ipynb](./serving/vertex_ai_tgi_gemma_multi_lora_adapters_deployment.ipynb) - This notebook showcases how to deploy Gemma 2 from the Hugging Face Hub with multiple LoRA adapters fine-tuned for different purposes such as coding, or SQL using Hugging Face's Text Generation Inference (TGI) Deep Learning Container (DLC) in combination with a custom handler on Vertex AI.
- [serving/vertex_ai_ollama_gemma2_rag_agent.ipynb](./serving/vertex_ai_ollama_gemma2_rag_agent.ipynb) - This notebooks provides steps and code to deploy an open source agentic RAG pipeline to Vertex AI Prediction using Ollama and a Gemma 2 model adapter.

### Fine-tuning

- [fine-tuning/vertex_ai_trl_fine_tuning_gemma.ipynb](./fine-tuning/vertex_ai_trl_fine_tuning_gemma.ipynb) - This notebooks provides steps and code to fine-tune Google Gemma with TRL via the Hugging Face PyTorch DLC for Training on Vertex AI.

### Evaluation

- [evaluation/vertex_ai_tgi_gemma_with_genai_evaluation.ipynb](./evaluation/vertex_ai_tgi_gemma_with_genai_evaluation.ipynb) - This notebooks provides steps and code to use the Vertex AI Gen AI Evaluation framework to evaluate Gemma 2 in a summarization task.

### Use cases

- [use-cases/bigquery_ml_llama_inference.ipynb](./use-cases/bigquery_ml_llama_inference.ipynb) - This notebook showcases a simple end-to-end process for extracting entities and performing data analytics using BigQuery in conjunction with an open-source text-generation Large Language Model (LLM). We use Meta's Llama 3.3 70B model as an example.
- [use-cases/cloud_run_ollama_gemma2_rag_qa.ipynb](./use-cases/cloud_run_ollama_gemma2_rag_qa.ipynb) - This notebooks provides steps and code to deploy an open source RAG pipeline to Cloud Run using Ollama and the Gemma 2 model.
- [use-cases/guess_app.ipynb](./use-cases/guess_app.ipynb) - This notebook shows how to build a "Guess Who or What" app using FLUX and Gemini.
