# Starting Model and Tuning Method Recommendation

## Available Models

- Gemma 3 27B IT (google/gemma-3-27b-it)
- Llama 3.1 8B (meta/llama3_1@llama-3.1-8b)
- Llama 3.1 8B Instruct (meta/llama3_1@llama-3.1-8b-instruct)
- Llama 3.2 1B Instruct (meta/llama3-2@llama-3.2-1b-instruct)
- Llama 3.2 3B Instruct (meta/llama3-2@llama-3.2-3b-instruct)
- Llama 3.3 70B Instruct (meta/llama3-3@llama-3.3-70b-instruct)
- Qwen 3 32B (qwen/qwen3@qwen3-32b)
- Llama 4 Scout 17B 16E Instruct (meta/llama4@llama-4-scout-17b-16e-instruct)

## Guidelines to follow for model Selection

Different families are suitable for different types of tasks.

- Qwen is a good choice for code generation or math based tasks.
- Gemma is a good choice for chat based tasks.
- Llama is an okay choice for other tasks.
- Only one model in the list Llama 3.1 8B is not an instruct model, this is
best suited for continuation tasks.

Gauge the complexity of the task by examining samples from the
dataset.

Tasks that are easier should be handled by smaller models, while more complex
tasks should be handled by larger models.

For example, a task that requires simple question answering can be handles by
the 1B or 3B models, while a task that requires complex reasoning should be
handled by either the Qwen 3 32B, Gemma 3 27B or Llama 3.3 70B model.
Any intermediate tasks can be handled by the 8B or 17B models.

Another aspect to consider is if the dataset is multi turn or needs tool calling
capabilities prefer the strongest models. Qwen 3 32B > Gemma 3 27B >
Llama 3.3 70B unless the user explicitly requests otherwise.
