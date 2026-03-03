"""Module for deploying tuned models to Vertex AI endpoints."""

import argparse
import logging

import vertexai  # type: ignore
from vertexai.preview import model_garden  # type: ignore


def deploy_tuned_model(
    project: str,
    location: str,
    artifacts_uri: str,
    machine_type: str,
    accelerator_type: str,
    accelerator_count: int,
) -> vertexai.aiplatform.Endpoint:
  """Deploys a tuned model to a Vertex AI endpoint."""
  vertexai.init(project=project, location=location)

  logging.info("Deploying model from %s...", artifacts_uri)
  tuned_model = model_garden.CustomModel(gcs_uri=artifacts_uri)

  endpoint = tuned_model.deploy(
      machine_type=machine_type,
      accelerator_type=accelerator_type,
      accelerator_count=accelerator_count,
  )

  logging.info("Model deployed to endpoint: %s", endpoint.resource_name)
  return endpoint


if __name__ == "__main__":
  parser = argparse.ArgumentParser(
      description="Deploy Tuned Model to Vertex Endpoint"
  )
  parser.add_argument("--project", required=True)
  parser.add_argument("--location", required=True)
  parser.add_argument(
      "--artifacts_uri",
      required=True,
      help="GCS path to postprocess/node-0/checkpoints/final",
  )
  parser.add_argument("--machine_type", required=True)
  parser.add_argument("--accelerator_type", required=True)
  parser.add_argument("--accelerator_count", type=int, required=True)

  args = parser.parse_args()
  deploy_tuned_model(**vars(args))
