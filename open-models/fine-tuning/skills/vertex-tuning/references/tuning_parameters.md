# Vertex AI Model Tuning Parameters

This reference guide details the parameters available for fine-tuning
models using Vertex AI's Supervised Fine-Tuning (SFT) service.

## Core Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `base_model` | `str` | N/A | The resource name or Model Garden ID of the base model (e.g., `meta/llama3_1@llama-3.1-8b`). |
| `tuning_mode` | `str` | `PEFT_ADAPTER` | The tuning method. Options: `FULL` (Full Fine-Tuning) or `PEFT_ADAPTER` (Parameter-Efficient Fine-Tuning). |
| `epochs` | `int` | `1` | Number of training epochs. |
| `learning_rate` | `float` | `2e-5` (Full), `1e-4` (PEFT) | The step size at each iteration while moving toward a minimum of a loss function. |
| `adapter_size` | `int` | `4` | The adapter size for PEFT. Options: `1, 4, 8, 16, 32`. |
| `train_dataset` | `str` | N/A | GCS URI to the training dataset (JSONL format). |
| `validation_dataset`| `str` | `None` | GCS URI to the validation dataset (JSONL format). |
| `output_uri` | `str` | N/A | GCS URI for storing model artifacts and logs. |

## Best Practices

1. **Dataset Size**: For SFT, aim for at least 100-1000 high-quality examples.
2. **Validation**: Always include a validation dataset (less than 5000 rows or 25% of training data) to monitor for overfitting.
3. **Checkpoints**: The service automatically saves the final model to the user-provided output location: `<output_uri>/postprocess/node-0/checkpoints/final`.

## Hardware Selection (Deployment)

When deploying the tuned model, consider the model size:

- **7B/8B models**: `g2-standard-12` (1x L4) or `n1-standard-8` (1x T4) for light inference. `g2-standard-12` is recommended for better performance.
- **70B models**: `a2-highgpu-8g` (8x A100) or multiple L4 GPUs may be required depending on quantization.

## Tuning Method Recommendation

Available tuning methods are

- `tuning_mode="FULL"`
- `tuning_mode="PEFT_ADAPTER"`

Choice between FULL and PEFT_ADAPTER depends on the size of the dataset and the
complexity of the task.

- For smaller datasets (less than 1000 examples) and simpler tasks, use
  PEFT_ADAPTER.
- For larger datasets (more than 1000 examples) and more complex tasks, use
  FULL.

Look for the output from the dataset preparation step to determine the size of
the dataset.

Treat this transition as continuous so as the dataset size increases use that
information to guide the rank of the peft adapter size in case the method is
being used.

## Limitations

Please ensure that your recommendations adhere to these allowed combinations:

```markdown
| Model | Tuning Modes | Max Sequence Length | Modalities |
| :--- | :--- | :--- | :--- |
| Gemma 3 27B IT | PEFT, Full | 8192 | Text |
| Llama 3.1 8B | PEFT, Full | 8192 | Text |
| Llama 3.1 8B Instruct | PEFT, Full | 8192 | Text |
| Llama 3.2 1B Instruct | Full | 8192 | Text |
| Llama 3.2 3B Instruct | Full | 8192 | Text |
| Llama 3.3 70B Instruct | PEFT, Full | 8192 | Text |
| Llama 4 Scout 17B 16E Instruct | PEFT | 2048 | Text, Images* |
| Qwen 3 32B | PEFT, Full | 8192 | Text |

\* Mixed datasets of both text-only and image examples are not supported. If there is at least one image example in the dataset, all text-only examples will be filtered out.
```
