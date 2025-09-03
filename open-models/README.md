# Open Models

This repository contains examples for deploying and fine-tuning open source models with Vertex AI.

## Notebooks

### Serving

- [get_started_with_model_garden_sdk.ipynb](./get_started_with_model_garden_sdk.ipynb) - This notebook showcase how to deploy and serve open models on Vertex AI using the Model Garden SDK, with simplified setup and streamlined configs.
- [serving/cloud_run_ollama_gemma3_inference.ipynb](./serving/cloud_run_ollama_gemma3_inference.ipynb) - This notebook showcase how to deploy Google Gemma 3 in Cloud Run using Ollama, with the objective to build a simple API for chat.
- [serving/cloud_run_vllm_gemma3_inference.ipynb](./serving/cloud_run_vllm_gemma3_inference.ipynb) - This notebook showcase how to deploy Google Gemma 3 in Cloud Run using vLLM, with the objective to build a simple API for chat.
- [serving/cloud_run_ollama_qwen3_inference.ipynb](./serving/cloud_run_ollama_qwen3_inference.ipynb) - This notebook shows how to deploy Qwen 3 in Cloud Run using Ollama, with the objective to build a simple AI Agent.
- [serving/vertex_ai_ollama_gemma2_rag_agent.ipynb](./serving/vertex_ai_ollama_gemma2_rag_agent.ipynb) - This notebooks provides steps and code to deploy an open source agentic RAG pipeline to Vertex AI Prediction using Ollama and a Gemma 2 model adapter.
- [serving/vertex_ai_pytorch_inference_paligemma_with_custom_handler.ipynb](./serving/vertex_ai_pytorch_inference_paligemma_with_custom_handler.ipynb) - This notebooks provides steps and code to deploy Google PaliGemma with the Hugging Face Python Inference DLC using a custom handler on Vertex AI.
- [serving/vertex_ai_pytorch_inference_pllum_with_custom_handler.ipynb](./serving/vertex_ai_pytorch_inference_pllum_with_custom_handler.ipynb) - This notebook shows how to deploy Polish Large Language Model (PLLuM) from the Hugging Face Hub on Vertex AI using the Hugging Face Deep Learning Container (DLC) for Pytorch Inference in combination with a custom handler.
- [serving/vertex_ai_text_generation_inference_gemma.ipynb](./serving/vertex_ai_text_generation_inference_gemma.ipynb) - This notebooks provides steps and code to deploy Google Gemma with the Hugging Face DLC for Text Generation Inference (TGI) on Vertex AI.
- [serving/vertex_ai_tgi_gemma_multi_lora_adapters_deployment.ipynb](./serving/vertex_ai_tgi_gemma_multi_lora_adapters_deployment.ipynb) - This notebook showcases how to deploy Gemma 2 from the Hugging Face Hub with multiple LoRA adapters fine-tuned for different purposes such as coding, or SQL using Hugging Face's Text Generation Inference (TGI) Deep Learning Container (DLC) in combination with a custom handler on Vertex AI.

### Fine-tuning

- [fine-tuning/vertex_ai_trl_fine_tuning_gemma.ipynb](./fine-tuning/vertex_ai_trl_fine_tuning_gemma.ipynb) - This notebooks provides steps and code to fine-tune Google Gemma with TRL via the Hugging Face PyTorch DLC for Training on Vertex AI.

### Evaluation

- [evaluation/vertex_ai_tgi_gemma_with_genai_evaluation.ipynb](./evaluation/vertex_ai_tgi_gemma_with_genai_evaluation.ipynb) - This notebooks provides steps and code to use the Vertex AI Gen AI Evaluation framework to evaluate Gemma 2 in a summarization task.
- [evaluation/vertex_ai_tgi_evaluate_llm_with_open_judge.ipynb](./evaluation/vertex_ai_tgi_evaluate_llm_with_open_judge.ipynb) - This notebooks shows how to use custom judge model to evaluate LLM-based application using the Autorater configuration in Gen AI Eval service.

### Use cases

- [use-cases/model_garden_litellm_inference.ipynb](./use-cases/model_garden_litellm_inference.ipynb) - This notebook showcases how to deploy an open-source model from Vertex AI Model Garden and serve inference through LiteLLM using an OpenAI-compatible API, including support for chat completion and function calling.
- [use-cases/bigquery_ml_llama_inference.ipynb](./use-cases/bigquery_ml_llama_inference.ipynb) - This notebook showcases a simple end-to-end process for extracting entities and performing data analytics using BigQuery in conjunction with an open-source text-generation Large Language Model (LLM). We use Meta's Llama 3.3 70B model as an example.
- [use-cases/cloud_run_ollama_gemma2_rag_qa.ipynb](./use-cases/cloud_run_ollama_gemma2_rag_qa.ipynb) - This notebooks provides steps and code to deploy an open source RAG pipeline to Cloud Run using Ollama and the Gemma 2 model.
- [use-cases/guess_app.ipynb](./use-cases/guess_app.ipynb) - This notebook shows how to build a "Guess Who or What" app using FLUX and Gemini.
- [vertex_ai_deepseek_smolagents.ipynb](./use-cases/vertex_ai_deepseek_smolagents.ipynb) - This notebook showcases how to deploy DeepSeek R1 Distill Qwen 7B from the Hugging Face Hub on Vertex AI using Vertex AI Model Garden. It also shows how to prototype and deploy a simple agent using HuggingFace's smol-agents library on Vertex AI Reasoning Engine.
