# Data Preparation for Vertex AI Model Tuning

Vertex AI Model Tuning requires training data in **JSON Lines (JSONL)** format
stored in Google Cloud Storage (GCS).

## Supported JSONL Formats

### 1. Conversational (Messages) Format
Recommended for chat-based models (Llama 3.1/3.2/3.3 Chat, Gemma 3 IT, etc.).

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"},
    {"role": "assistant", "content": "The capital of France is Paris."}
  ]
}
```

### 2. Instruction (Prompt/Completion) Format
Suitable for base models or simple completion tasks.

```json
{
  "prompt": "Summarize the following text: [TEXT]",
  "completion": "[SUMMARY]"
}
```

## Dataset Requirements

- **File Type**: Must be `.jsonl`.
- **Encoding**: UTF-8.
- **Location**: Must be in a GCS bucket (e.g., `gs://my-bucket/train.jsonl`).
- **Validation Split**: A separate validation file is optional but recommended. It must be no more than 25% of the training dataset size.

## Bucket Considerations

If a bucket does not exist, create one in the same region as your tuning job:

```bash
gcloud storage buckets create gs://YOUR_BUCKET_NAME --location=YOUR_LOCATION
```

## Formatting Best Practices

1. **Quality over Quantity**: 100 high-quality examples often outperform 1,000 noisy ones.
2. **Consistency**: Use consistent formatting for system prompts and instruction styles.
3. **No Empty Values**: Ensure every example has a valid prompt/user message and completion/assistant response. Use the [preparation script](/cloud/ai/platform/modelgarden/agent_skills/vertex-tuning/scripts/prepare_dataset.py) to validate this.
