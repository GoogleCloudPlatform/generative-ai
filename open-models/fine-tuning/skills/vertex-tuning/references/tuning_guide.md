# Vertex AI Model Tuning Heuristics and Concepts

This guide details the core concepts of fine-tuning and provides heuristics for
adjusting hyperparameters based on your specific dataset.

## Core Tuning Concepts

### Tuning Modes

- **FULL**: Updates all parameters of the model. Requires more GPU memory and a larger dataset to avoid catastrophic forgetting.
- **PEFT_ADAPTER**: Parameter-Efficient Fine-Tuning. Only a small set of "adapter" weights are trained. Faster, uses less memory, and is less prone to overfitting on small datasets.

### Hyperparameters

- **Epochs**: Number of times the model sees the entire dataset.
- **Learning Rate**: Step size for optimization. Too high can cause instability; too low can lead to very slow convergence.
- **Adapter Size (Rank)**: For PEFT, this determines the capacity of the adapters. Higher rank allows more complex learning but increases the risk of overfitting.

## Dataset Heuristics

The size and quality of your dataset should dictate your parameter choices. Refer to [Models Catalog](models.md) for baseline values, then adjust as follows:

### 1. Dataset Size Implications

| Dataset Size | Tuning Mode Recommendation | Learning Rate Adjustment | Epochs Recommendation |
| :--- | :--- | :--- | :--- |
| **< 100 examples** | PEFT_ADAPTER (Rank 8) | Lower than baseline | 1-2 |
| **100 - 1000 examples** | PEFT_ADAPTER (Rank 16/32) | Baseline | 3 |
| **> 1000 examples** | FULL or PEFT (Rank 32) | Higher than baseline | 3-5 |

### 2. General Best Practices

- **Overfitting**: If validation loss starts increasing while training loss decreases, you are overfitting. Reduce epochs or decrease the learning rate.
- **Underfitting**: If both training and validation loss remain high, increase the learning rate or use more epochs.
- **Validation**: Always use a validation set to monitor performance. If not provided, a 10-20% split is highly recommended.
- **Checkpoints**: The final model is always saved to `<output_uri>/postprocess/node-0/checkpoints/final`.

## Hardware and Limitations
For specific hardware recommendations and sequence length limits per model, please refer to the [Models Catalog](models.md).
