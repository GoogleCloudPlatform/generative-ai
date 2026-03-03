# Data Formatting for Vertex AI Model Tuning

Vertex AI Model Tuning requires training data in **JSON Lines (JSONL)**
format. Each line must be a valid JSON object representing a single training
example.

## Supported Formats

### 1. Conversational (Messages) Format
Recommended for chat-based models (Llama 3 Chat, Gemma IT, etc.).

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

- **File Type**: `.jsonl`
- **Location**: Must be uploaded to a Google Cloud Storage (GCS) bucket.
- **Validation Split**: If provided, it must be less than 5,000 rows AND less than 25% of the training dataset size.
- **Encoding**: UTF-8.

## Sequence Length Limitations

Each model has a maximum sequence length (context window) supported during
tuning. Examples exceeding this limit may be truncated.

Please refer to the [official documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/models/open-model-tuning)
for the latest maximum sequence length limits for specific models and tuning
modes.

*Note: As a rule of thumb, 1 token is approximately 4 characters of
English text.*

## Bucket Considerations

If the user has not provided a bucket name create one using the following
command with the location same as the tuning job location.

```bash
gcloud storage buckets create gs://vertex-tuning-agent --location=BUCKET_LOCATION
```

## Preparation Workflow

1. **Collect Data**: Gather your raw data in CSV, JSONL, Parquet, or from
   Hugging Face.
2. **Apply Template**: Format each example using a template appropriate for
   your target model (e.g., Llama 3 prompt template).
3. **Convert to JSONL**: Save the formatted examples to a `.jsonl` file.
4. **Upload to GCS**: Use `gcloud storage cp` to move the file to your bucket.

```bash
gcloud storage cp dataset.jsonl gs://your-bucket/path/dataset.jsonl
```
