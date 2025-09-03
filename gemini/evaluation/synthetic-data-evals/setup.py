#!/usr/bin/env python
# setup_vertex_agent_resources.py

import os
import subprocess

from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import aiplatform
from huggingface_hub import get_token


def update_env_file(key, value):
    """Update a specific key in the .env file or add it if not present."""
    env_path = ".env"

    # Create .env file if it doesn't exist
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write(f"{key}={value}\n")
        return

    # Read existing content
    with open(env_path, "r") as f:
        lines = f.readlines()

    # Check if key exists and update it
    key_exists = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            key_exists = True
            break

    # Add key if it doesn't exist
    if not key_exists:
        lines.append(f"{key}={value}\n")

    # Write updated content
    with open(env_path, "w") as f:
        f.writelines(lines)


def authenticate_gcloud():
    """Help user authenticate with Google Cloud."""
    print("\n=== Google Cloud Authentication Required ===")
    print("Your Google Cloud credentials were not found.")
    print("Would you like to run 'gcloud auth application-default login' now? (y/n)")

    response = input().lower()
    if response != "y":
        print(
            "Authentication skipped. Please authenticate manually and run this script again."
        )
        print("Run: gcloud auth application-default login")
        return False

    try:
        print("\nLaunching Google Cloud authentication...")
        subprocess.run(["gcloud", "auth", "application-default", "login"], check=True)
        print("Authentication successful!")
        return True
    except subprocess.CalledProcessError:
        print("Authentication failed. Please try again manually.")
        print("Run: gcloud auth application-default login")
        return False
    except FileNotFoundError:
        print("Google Cloud SDK (gcloud) not found.")
        print(
            "Please install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
        )
        return False


def setup_vertex_resources():
    """Set up Vertex AI resources needed for the agent."""
    print("Setting up Vertex AI resources...")

    # Get Google Cloud credentials
    try:
        credentials, project_id = default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    except DefaultCredentialsError:
        print("Google Cloud credentials not found.")
        if not authenticate_gcloud():
            return False

        # Try again after authentication
        try:
            credentials, project_id = default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        except Exception as e:
            print(f"Error getting credentials after authentication: {e}")
            return False

    # Set location
    location = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

    # Initialize Vertex AI
    aiplatform.init(project=project_id, location=location)

    print(f"Initialized Vertex AI with project: {project_id}, location: {location}")

    # Check for existing DeepSeek model
    model_id = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
    model_display_name = model_id.replace("/", "--").lower()

    # List existing models
    models = aiplatform.Model.list(filter=f"display_name={model_display_name}")

    if models:
        print(f"Found existing DeepSeek model: {model_display_name}")
        deepseek_model = models[0]
    else:
        print("DeepSeek model not found. Would you like to register it? (y/n)")
        response = input().lower()

        if response != "y":
            print("Model registration skipped. Exiting setup.")
            return False

        print("Registering DeepSeek model. This may take a while...")
        try:
            # Get Hugging Face token
            hf_token = get_token()
            if not hf_token:
                print(
                    "Hugging Face token not found. Please run 'huggingface-cli login' first."
                )
                return False

            # Register the model
            deepseek_model = aiplatform.Model.upload(
                display_name=model_display_name,
                serving_container_image_uri="us-docker.pkg.dev/deeplearning-platform-release/vertex-model-garden/vllm-inference.cu121.0-6.ubuntu2204.py310",
                serving_container_args=[
                    "python",
                    "-m",
                    "vllm.entrypoints.api_server",
                    "--host=0.0.0.0",
                    "--port=8080",
                    f"--model={model_id}",
                    "--tensor-parallel-size=1",
                    "--max-model-len=16384",
                    "--enforce-eager",
                ],
                serving_container_ports=[8080],
                serving_container_predict_route="/generate",
                serving_container_health_route="/ping",
                serving_container_environment_variables={
                    "HF_TOKEN": hf_token,
                    "DEPLOY_SOURCE": "script",
                },
            )
            print(
                f"DeepSeek model registered successfully: {deepseek_model.resource_name}"
            )
        except Exception as e:
            print(f"Error registering model: {e}")
            return False

    # Check for existing endpoint
    endpoint_display_name = f"{model_display_name}-endpoint"
    endpoints = aiplatform.Endpoint.list(filter=f"display_name={endpoint_display_name}")

    if endpoints:
        print(f"Found existing endpoint: {endpoint_display_name}")
        deepseek_endpoint = endpoints[0]
        endpoint_id = deepseek_endpoint.name
    else:
        print(f"Endpoint not found. Creating new endpoint: {endpoint_display_name}")
        try:
            deepseek_endpoint = aiplatform.Endpoint.create(
                display_name=endpoint_display_name
            )
            endpoint_id = deepseek_endpoint.name

            # Deploy model to endpoint
            print("Deploying model to endpoint. This may take 15-20 minutes...")
            deployed_model = deepseek_model.deploy(
                endpoint=deepseek_endpoint,
                machine_type="g2-standard-12",
                accelerator_type="NVIDIA_L4",
                accelerator_count=1,
                sync=True,
            )
            print(f"Model deployed successfully to endpoint: {endpoint_id}")
        except Exception as e:
            print(f"Error creating/deploying endpoint: {e}")
            return False

    # Extract the endpoint ID from the full resource name
    endpoint_id_short = endpoint_id.split("/")[-1]

    # Update .env file with the configuration
    # Check and fix .env file if it doesn't end with a newline
    try:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                content = f.read()

            if content and not content.endswith("\n"):
                print("Adding missing newline to .env file...")
                with open(env_path, "a") as f:
                    f.write("\n")
                print(".env file fixed.")
    except Exception as e:
        print(f"Warning: Could not check/fix .env file: {e}")

    update_env_file("VERTEX_PROJECT_ID", project_id)
    update_env_file("VERTEX_LOCATION", location)
    update_env_file("VERTEX_MODEL_ID", "google/gemini-1.5-flash")  # For the main agent
    update_env_file("VERTEX_ENDPOINT_ID", "openapi")  # For Gemini
    update_env_file("DEEPSEEK_ENDPOINT_ID", endpoint_id_short)  # For DeepSeek

    print("\nEnvironment variables updated in .env file:")
    print(f"VERTEX_PROJECT_ID: {project_id}")
    print(f"VERTEX_LOCATION: {location}")
    print("VERTEX_MODEL_ID: google/gemini-1.5-flash")
    print("VERTEX_ENDPOINT_ID: openapi")
    print(f"DEEPSEEK_ENDPOINT_ID: {endpoint_id_short}")

    return True


if __name__ == "__main__":
    if setup_vertex_resources():
        print("\nVertex AI resources setup complete. You can now use the agent.")
        print("Run your agent with: python your_agent_script.py")
    else:
        print(
            "\nVertex AI resources setup failed. Please check the error messages above."
        )
