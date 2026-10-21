#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Deploy DiffusionGemma 26B-A4B with official vLLM on the Gemini platform.

Deploys Google DeepMind's DiffusionGemma 26B-A4B
(`nvidia/diffusiongemma-26B-A4B-it-NVFP4`) using the official upstream vLLM
container (`docker.io/vllm/vllm-openai:v0.31.0`) on the Gemini platform
(`1x NVIDIA_L4` GPU) for single-step structured diffusion reads.

Usage:
    # 1. Create an Artifact Registry repository and mirror vllm-openai:v0.31.0
    #    once via Cloud Build (no local Docker daemon required).
    gcloud artifacts repositories create containers \\
        --repository-format=docker \\
        --location=us \\
        --project=your-project-id
    gcloud builds submit --no-source --project=your-project-id \\
        --config=/dev/stdin <<'EOF'
    steps:
      - name: 'gcr.io/go-containerregistry/crane:latest'
        args:
          - 'copy'
          - '--platform=linux/amd64'
          - 'docker.io/vllm/vllm-openai:v0.31.0'
          - 'us-docker.pkg.dev/$PROJECT_ID/containers/vllm-openai:v0.31.0'
    EOF

    # 2. Deploy official vLLM + DiffusionGemma on g2-standard-8 (1x L4).
    python3 deploy_diffusiongemma.py --project your-project-id \\
        --region us-central1

    # 3. Undeploy and delete the endpoint and model to stop GPU billing.
    python3 deploy_diffusiongemma.py --project your-project-id \\
        --region us-central1 --delete
"""

import argparse
import json
import os

from google.cloud import aiplatform

import config


def find_endpoint_by_name(name: str) -> aiplatform.Endpoint | None:
    """Returns an existing Endpoint matching display_name, or None."""
    endpoints = aiplatform.Endpoint.list(filter=f'display_name="{name}"')
    return endpoints[0] if endpoints else None


def find_model_by_name(name: str) -> aiplatform.Model | None:
    """Returns an existing Model matching display_name, or None."""
    models = aiplatform.Model.list(filter=f'display_name="{name}"')
    return models[0] if models else None


def _build_vllm_serve_args(
    hf_model_id: str = config.HF_MODEL_ID,
    served_model_name: str = config.SERVED_MODEL_NAME,
    port: int = 8080,
    canvas_len: int = 64,
    max_num_seqs: int = 16,
    max_model_len: int = 4096,
    gpu_util: float = 0.92,
) -> list[str]:
    """Builds CLI flags for `vllm serve` in the vllm-openai Docker container."""
    diffusion_cfg = json.dumps({"canvas_length": canvas_len})
    mm_limit_cfg = json.dumps({"image": 0, "video": 0})
    gen_override_cfg = json.dumps({"max_new_tokens": None})
    return [
        # Model weights on Hugging Face and short OpenAI API model alias.
        hf_model_id,
        f"--served-model-name={served_model_name}",
        # Bind address and port expected by Gemini platform Online Prediction.
        "--host=0.0.0.0",
        f"--port={port}",
        # Block-diffusion width and max top_logprobs per token.
        f"--diffusion-config={diffusion_cfg}",
        "--max-logprobs=32",
        # Clear default max_new_tokens so per-request max_tokens takes effect.
        f"--override-generation-config={gen_override_cfg}",
        # Gemma 4 chat-template parsers for reasoning and tool calls.
        "--enable-auto-tool-choice",
        "--tool-call-parser=gemma4",
        "--reasoning-parser=gemma4",
        # Latency optimizations (KV prefix cache + overlapped CPU/GPU steps).
        "--enable-prefix-caching",
        "--async-scheduling",
        # Fit 17 GB NVFP4 weights + KV cache inside 1x 24 GB NVIDIA_L4 GPU.
        # Disable multimodal vision/video encoders for text-only.
        f"--limit-mm-per-prompt={mm_limit_cfg}",
        # Use Triton attention backend for bidirectional diffusion masks.
        "--attention-backend=TRITON_ATTN",
        f"--max-num-seqs={max_num_seqs}",
        f"--max-model-len={max_model_len}",
        f"--gpu-memory-utilization={gpu_util}",
    ]


def _build_vllm_container_env(hf_token: str | None = None) -> dict[str, str]:
    """Builds environment variables for the vLLM serving container."""
    env: dict[str, str] = {"VLLM_USE_V2_MODEL_RUNNER": "1"}
    token = hf_token if hf_token is not None else os.environ.get("HF_TOKEN")
    if token:
        env["HF_TOKEN"] = token
    return env


def deploy_model_to_endpoint(
    project: str,
    name: str = config.ENDPOINT_ID,
    hf_model_id: str = config.HF_MODEL_ID,
    served_model_name: str = config.SERVED_MODEL_NAME,
    image: str | None = None,
    artifact_uri: str | None = None,
    port: int = 8080,
    predict_route: str | None = None,
    health_route: str | None = None,
    machine_type: str = "g2-standard-8",
    accelerator_type: str = "NVIDIA_L4",
    accelerator_count: int = 1,
    max_model_len: int = 4096,
    max_num_seqs: int = 16,
    gpu_util: float = 0.92,
    canvas_len: int = 64,
    min_replicas: int = 1,
    max_replicas: int = 1,
    dedicated: bool = True,
    redeploy: bool = False,
) -> aiplatform.Endpoint:
    """Uploads the vLLM model and deploys it to a Gemini platform endpoint."""
    endpoint = find_endpoint_by_name(name)
    if endpoint and endpoint.list_models():
        if not redeploy:
            print(
                f"Endpoint '{endpoint.resource_name}' is already deployed;"
                " reusing it."
            )
            return endpoint
        print(
            f"Undeploying existing models on '{endpoint.resource_name}'"
            " for redeployment..."
        )
        endpoint.undeploy_all()

    existing_model = find_model_by_name(name)
    image_uri = image or config.DEFAULT_IMAGE_TEMPLATE.format(project=project)
    resolved_predict_route = predict_route or "/v1/chat/completions"
    resolved_health_route = health_route or "/health"
    vllm_args = _build_vllm_serve_args(
        hf_model_id=hf_model_id,
        served_model_name=served_model_name,
        port=port,
        canvas_len=canvas_len,
        max_num_seqs=max_num_seqs,
        max_model_len=max_model_len,
        gpu_util=gpu_util,
    )
    container_env = _build_vllm_container_env()

    print(
        f"Uploading model '{name}' with official vLLM container:\n"
        f"  {image_uri}\n"
        f"  model={hf_model_id},"
        f" max_model_len={max_model_len},"
        f" max_num_seqs={max_num_seqs},"
        f" gpu_util={gpu_util}"
    )
    parent_model = existing_model.resource_name if existing_model else None
    model = aiplatform.Model.upload(
        display_name=name,
        model_id=None if existing_model else name,
        parent_model=parent_model,
        artifact_uri=artifact_uri,
        serving_container_image_uri=image_uri,
        serving_container_command=["vllm", "serve"],
        serving_container_args=vllm_args,
        serving_container_ports=[port],
        serving_container_predict_route=resolved_predict_route,
        serving_container_health_route=resolved_health_route,
        serving_container_environment_variables=container_env,
    )

    if not endpoint:
        print(f"Creating endpoint '{name}' (dedicated={dedicated})...")
        endpoint = aiplatform.Endpoint.create(
            display_name=name,
            endpoint_id=name,
            dedicated_endpoint_enabled=dedicated,
        )

    print(
        f"Deploying model to endpoint on {machine_type}"
        f" ({accelerator_count}x {accelerator_type})..."
    )
    endpoint.deploy(
        model=model,
        deployed_model_display_name=name,
        machine_type=machine_type,
        accelerator_type=accelerator_type if accelerator_count else None,
        accelerator_count=accelerator_count or None,
        min_replica_count=min_replicas,
        max_replica_count=max_replicas,
    )

    print("\nDeployment Ready!")
    print(f"  Endpoint resource: {endpoint.resource_name}")
    print(f"  Dedicated DNS:     {endpoint.dedicated_endpoint_dns}")
    return endpoint


def delete_endpoint_and_model(name: str = config.ENDPOINT_ID) -> None:
    """Undeploys all models and deletes the endpoint and model via the SDK."""
    endpoint = find_endpoint_by_name(name)
    if endpoint:
        print(
            "Undeploying all models and deleting endpoint"
            f" '{endpoint.resource_name}'..."
        )
        endpoint.delete(force=True)
    else:
        print(f"Endpoint '{name}' not found; skipping endpoint deletion.")

    model = find_model_by_name(name)
    if model:
        print(f"Deleting model '{model.resource_name}'...")
        model.delete()
    else:
        print(f"Model '{name}' not found; skipping model deletion.")

    print(f"Deleted '{name}' cleanly.")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--project",
        default=config.resolve_default_project(),
        help="Google Cloud project ID (defaults to GOOGLE_CLOUD_PROJECT/ADC)",
    )
    ap.add_argument(
        "--region",
        default=config.REGION,
        help="Google Cloud region (defaults to GOOGLE_CLOUD_REGION)",
    )
    ap.add_argument(
        "--name",
        default=config.ENDPOINT_ID,
        help="Model and endpoint display name",
    )
    ap.add_argument(
        "--hf-model-id",
        default=config.HF_MODEL_ID,
        help="Hugging Face model ID for DiffusionGemma weights",
    )
    ap.add_argument(
        "--served-model-name",
        default=config.SERVED_MODEL_NAME,
        help="Model name exposed by vLLM (--served-model-name)",
    )
    ap.add_argument(
        "--image",
        default=os.environ.get("VLLM_IMAGE_URI") or None,
        help="Artifact Registry URI for vllm/vllm-openai:v0.31.0",
    )
    ap.add_argument(
        "--artifact-uri", help="Optional gs:// checkpoint URI to serve instead"
    )
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--predict-route", default=None)
    ap.add_argument("--health-route", default=None)
    ap.add_argument(
        "--machine-type",
        default="g2-standard-8",
        help="VM machine type (default: g2-standard-8 with 1x NVIDIA_L4 24GB)",
    )
    ap.add_argument("--accelerator-type", default="NVIDIA_L4")
    ap.add_argument("--accelerator-count", type=int, default=1)
    ap.add_argument(
        "--max-model-len",
        type=int,
        default=4096,
        help=(
            "vLLM --max-model-len (default 4096 to fit 17GB NVFP4 weights + KV"
            " cache on a 24GB NVIDIA_L4 GPU)"
        ),
    )
    ap.add_argument(
        "--max-num-seqs",
        type=int,
        default=16,
        help="vLLM --max-num-seqs concurrent sequences for GPU batching",
    )
    ap.add_argument(
        "--gpu-util",
        type=float,
        default=0.92,
        help="vLLM --gpu-memory-utilization fraction (default 0.92 for L4)",
    )
    ap.add_argument(
        "--canvas-len",
        type=int,
        default=64,
        help="DiffusionGemma canvas_length in --diffusion-config",
    )
    ap.add_argument("--min-replicas", type=int, default=1)
    ap.add_argument("--max-replicas", type=int, default=1)
    ap.add_argument(
        "--dedicated",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use dedicated endpoint DNS (required for rawPredict)",
    )
    ap.add_argument(
        "--redeploy",
        action="store_true",
        help="Undeploy existing model and redeploy with updated flags",
    )
    ap.add_argument(
        "--delete",
        "--cleanup",
        action="store_true",
        help="Undeploy all models and delete the endpoint and model",
    )
    args = ap.parse_args()
    if not args.project:
        ap.error(
            "Project ID must be provided via --project, GOOGLE_CLOUD_PROJECT,"
            " or gcloud default credentials."
        )

    aiplatform.init(project=args.project, location=args.region)

    if args.delete:
        delete_endpoint_and_model(name=args.name)
        return

    deploy_model_to_endpoint(
        project=args.project,
        name=args.name,
        hf_model_id=args.hf_model_id,
        served_model_name=args.served_model_name,
        image=args.image,
        artifact_uri=args.artifact_uri,
        port=args.port,
        predict_route=args.predict_route,
        health_route=args.health_route,
        machine_type=args.machine_type,
        accelerator_type=args.accelerator_type,
        accelerator_count=args.accelerator_count,
        max_model_len=args.max_model_len,
        max_num_seqs=args.max_num_seqs,
        gpu_util=args.gpu_util,
        canvas_len=args.canvas_len,
        min_replicas=args.min_replicas,
        max_replicas=args.max_replicas,
        dedicated=args.dedicated,
        redeploy=args.redeploy,
    )


if __name__ == "__main__":
    main()
