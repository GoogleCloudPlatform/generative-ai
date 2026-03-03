# Vertex AI Supported Models and Recommendations

This reference catalog provides technical specifications, tuning
recommendations, and deployment hardware requirements for supported models in
Vertex AI.

## Supported Models Catalog

Available models can be found in Google Cloud [documentation](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/open-model-tuning#supported-models)
This is the list of open models that are available for tuning; do not suggest
any other models besides the one listed here.
Each model has some [limitations](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/open-model-tuning#limitations) for tuning.

## Model Selection Guidelines

Choose a model family based on your task type:

- **Qwen**: Best for code generation or complex math-based tasks.
- **Gemma**: Optimized for chat-based interactions and creative writing.
- **Llama (Instruct)**: Strong general-purpose chat/instruction models.
- **Llama (Base/Scout)**: Best for continuation tasks or building custom instruction-tuned models.

**Complexity Heuristics**:

- **Simple (QA, Extraction)**: 1B - 3B models.
- **Intermediate (Summarization, Reasoning)**: 8B - 17B models.
- **Complex (Multi-turn, Tool use, Deep reasoning)**: 27B - 70B models.

## Baseline Hyperparameter Recommendations

These values are starting points and should be adjusted based on your dataset
size.

| Model | Tuning Mode | Learning Rate | Epochs | Adapter Size (PEFT) |
| :--- | :--- | :--- | :--- | :--- |
| Gemma 3 27B IT | PEFT | 2.0E-4 | 3 | 32 |
| Gemma 3 27B IT | Full | 2.0E-4 | 3 | N/A |
| Llama 3.1 8B | PEFT | 2.0E-4 | 3 | 16 |
| Llama 3.1 8B | Full | 2.0E-4 | 3 | N/A |
| Llama 3.1 8B Instruct | PEFT | 2.0E-4 | 3 | 16 |
| Llama 3.1 8B Instruct | Full | 2.0E-4 | 3 | N/A |
| Llama 3.2 1B Instruct | Full | 1.5E-6 | 3 | N/A |
| Llama 3.2 3B Instruct | Full | 1.0E-7 | 3 | N/A |
| Llama 3.3 70B Instruct | PEFT | 5.0E-5 | 3 | 16 |
| Llama 3.3 70B Instruct | Full | 5.0E-5 | 3 | N/A |
| Llama 4 Scout 17B 16E | PEFT | 2.0E-5 | 3 | 16 |
| Qwen 3 32B | PEFT | 2.0E-4 | 3 | 16 |
| Qwen 3 32B | Full | 2.0E-4 | 3 | N/A |
