"""Module for launching Vertex AI model tuning jobs."""

import argparse
import logging

import vertexai  # type: ignore
from vertexai.tuning import sft  # type: ignore
from vertexai.tuning import SourceModel  # type: ignore


def tune_model(
    project: str,
    location: str,
    bucket: str,
    base_model: str,
    train_dataset: str,
    validation_dataset: str | None,
    output_uri: str,
    epochs: int,
    learning_rate: float,
    tuning_mode: str,
    adapter_size: int | None = None,
) -> sft.SupervisedTuningJob:
  """Launches a Vertex AI model tuning job."""
  vertexai.init(project=project, location=location, staging_bucket=bucket)

  source_model = SourceModel(base_model=base_model)

  tuning_job = sft.train(
      source_model=source_model,
      train_dataset=train_dataset,
      validation_dataset=validation_dataset if validation_dataset else None,
      epochs=epochs,
      learning_rate=learning_rate,
      tuning_mode=tuning_mode,
      adapter_size=adapter_size,
      output_uri=output_uri,
      labels={"mg-source": "vertex-tuning-skill"},
  )

  logging.info("Tuning job launched: %s", tuning_job.resource_name)
  logging.info(
      "View job in console:"
      " https://console.cloud.google.com/vertex-ai/locations/%s/tuning-jobs/%s?project=%s",
      location,
      tuning_job.name,
      project,
  )
  return tuning_job


if __name__ == "__main__":
  parser = argparse.ArgumentParser(
      description="Launch Vertex AI Model Tuning Job"
  )
  parser.add_argument("--project", required=True)
  parser.add_argument("--location", required=True)
  parser.add_argument("--bucket", required=True)
  parser.add_argument("--base_model", required=True)
  parser.add_argument("--train_dataset", required=True)
  parser.add_argument(
      "--validation_dataset", help="Optional validation dataset URI"
  )
  parser.add_argument("--output_uri", required=True)
  parser.add_argument("--epochs", type=int, required=True)
  parser.add_argument("--learning_rate", type=float, required=True)
  parser.add_argument(
      "--tuning_mode", choices=["FULL", "PEFT_ADAPTER"], required=True
  )
  parser.add_argument(
      "--adapter_size",
      type=int,
      choices=[1, 4, 8, 16, 32],
      help="Adapter size for PEFT",
  )

  args = parser.parse_args()
  tune_model(
      project=args.project,
      location=args.location,
      bucket=args.bucket,
      base_model=args.base_model,
      train_dataset=args.train_dataset,
      validation_dataset=args.validation_dataset,
      output_uri=args.output_uri,
      epochs=args.epochs,
      learning_rate=args.learning_rate,
      tuning_mode=args.tuning_mode,
      adapter_size=args.adapter_size,
  )
