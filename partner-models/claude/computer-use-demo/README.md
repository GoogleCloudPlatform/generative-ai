# Anthropic Computer Use Demo

> [!CAUTION]
> Computer use is a beta feature. Please be aware that computer use poses unique risks that are distinct from standard API features or chat interfaces. These risks are heightened when using computer use to interact with the internet. To minimize risks, consider taking precautions such as:
>
> 1. Use a dedicated virtual machine or container with minimal privileges to prevent direct system attacks or accidents.
> 2. Avoid giving the model access to sensitive data, such as account login information, to prevent information theft.
> 3. Limit internet access to an allowlist of domains to reduce exposure to malicious content.
> 4. Ask a human to confirm decisions that may result in meaningful real-world consequences as well as any tasks requiring affirmative consent, such as accepting cookies, executing financial transactions, or agreeing to terms of service.
>
> In some circumstances, Claude will follow commands found in content even if it conflicts with the user's instructions. For example, instructions on webpages or contained in images may override user instructions or cause Claude to make mistakes. We suggest taking precautions to isolate Claude from sensitive data and actions to avoid risks related to prompt injection.
>
> Finally, please inform end users of relevant risks and obtain their consent prior to enabling computer use in your own products.

This repository helps you get started with computer use on Claude, with reference implementations of:

* Build files to create a Docker container with all necessary dependencies
* A computer use agent loop using the Anthropic API, Bedrock, or Vertex to access the updated Claude 3.5 Sonnet model
* Anthropic-defined computer use tools
* A streamlit app for interacting with the agent loop

Please use [this form](https://forms.gle/BT1hpBrqDPDUrCqo7) to provide feedback on the quality of the model responses, the API itself, or the quality of the documentation - we cannot wait to hear from you!

> [!IMPORTANT]
> The Beta API used in this reference implementation is subject to change. Please refer to the [API release notes](https://docs.anthropic.com/en/release-notes/api) for the most up-to-date information.

> [!IMPORTANT]
> The components are weakly separated: the agent loop runs in the container being controlled by Claude, can only be used by one session at a time, and must be restarted or reset between sessions if necessary.

## Quickstart: running the Docker container

### Anthropic API

> [!TIP]
> You can find your API key in the [Anthropic Console](https://console.anthropic.com/).

```bash
export ANTHROPIC_API_KEY=%your_api_key%
docker run \
    -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
    -v $HOME/.anthropic:/home/computeruse/.anthropic \
    -p 5900:5900 \
    -p 8501:8501 \
    -p 6080:6080 \
    -p 8080:8080 \
    -it ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest
```

Once the container is running, see the [Accessing the demo app](#accessing-the-demo-app) section below for instructions on how to connect to the interface.

### Bedrock

> [!TIP]
> To use the new Claude 3.5 Sonnet on Bedrock, you first need to [request model access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html).

You'll need to pass in AWS credentials with appropriate permissions to use Claude on Bedrock.

You have a few options for authenticating with Bedrock. See the [boto3 documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#environment-variables) for more details and options.

#### Option 1: (suggested) Use the host's AWS credentials file and AWS profile

```bash
export AWS_PROFILE=<your_aws_profile>
docker run \
    -e API_PROVIDER=bedrock \
    -e AWS_PROFILE=$AWS_PROFILE \
    -e AWS_REGION=us-west-2 \
    -v $HOME/.aws:/home/computeruse/.aws \
    -v $HOME/.anthropic:/home/computeruse/.anthropic \
    -p 5900:5900 \
    -p 8501:8501 \
    -p 6080:6080 \
    -p 8080:8080 \
    -it ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest
```

Once the container is running, see the [Accessing the demo app](#accessing-the-demo-app) section below for instructions on how to connect to the interface.

#### Option 2: Use an access key and secret

```bash
export AWS_ACCESS_KEY_ID=%your_aws_access_key%
export AWS_SECRET_ACCESS_KEY=%your_aws_secret_access_key%
export AWS_SESSION_TOKEN=%your_aws_session_token%
docker run \
    -e API_PROVIDER=bedrock \
    -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
    -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
    -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN \
    -e AWS_REGION=us-west-2 \
    -v $HOME/.anthropic:/home/computeruse/.anthropic \
    -p 5900:5900 \
    -p 8501:8501 \
    -p 6080:6080 \
    -p 8080:8080 \
    -it ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest
```

Once the container is running, see the [Accessing the demo app](#accessing-the-demo-app) section below for instructions on how to connect to the interface.

### Vertex

You'll need to pass in Google Cloud credentials with appropriate permissions to use Claude on Vertex.

```bash
docker build . -t computer-use-demo
gcloud auth application-default login
export VERTEX_REGION=%your_vertex_region%
export VERTEX_PROJECT_ID=%your_vertex_project_id%
docker run \
    -e API_PROVIDER=vertex \
    -e CLOUD_ML_REGION=$VERTEX_REGION \
    -e ANTHROPIC_VERTEX_PROJECT_ID=$VERTEX_PROJECT_ID \
    -v $HOME/.config/gcloud/application_default_credentials.json:/home/computeruse/.config/gcloud/application_default_credentials.json \
    -p 5900:5900 \
    -p 8501:8501 \
    -p 6080:6080 \
    -p 8080:8080 \
    -it computer-use-demo
```

Once the container is running, see the [Accessing the demo app](#accessing-the-demo-app) section below for instructions on how to connect to the interface.

This example shows how to use the Google Cloud Application Default Credentials to authenticate with Vertex.

You can also set `GOOGLE_APPLICATION_CREDENTIALS` to use an arbitrary credential file, see the [Google Cloud Authentication documentation](https://cloud.google.com/docs/authentication/application-default-credentials#GAC) for more details.

### Accessing the demo app

Once the container is running, open your browser to [http://localhost:8080](http://localhost:8080) to access the combined interface that includes both the agent chat and desktop view.

The container stores settings like the API key and custom system prompt in `~/.anthropic/`. Mount this directory to persist these settings between container runs.

Alternative access points:

- Streamlit interface only: [http://localhost:8501](http://localhost:8501)
- Desktop view only: [http://localhost:6080/vnc.html](http://localhost:6080/vnc.html)
- Direct VNC connection: `vnc://localhost:5900` (for VNC clients)

## Screen size

Environment variables `WIDTH` and `HEIGHT` can be used to set the screen size. For example:

```bash
docker run \
    -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
    -v $HOME/.anthropic:/home/computeruse/.anthropic \
    -p 5900:5900 \
    -p 8501:8501 \
    -p 6080:6080 \
    -p 8080:8080 \
    -e WIDTH=1920 \
    -e HEIGHT=1080 \
    -it ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest
```

We do not recommend sending screenshots in resolutions above [XGA/WXGA](https://en.wikipedia.org/wiki/Display_resolution_standards#XGA) to avoid issues related to [image resizing](https://docs.anthropic.com/en/docs/build-with-claude/vision#evaluate-image-size).
Relying on the image resizing behavior in the API will result in lower model accuracy and slower performance than implementing scaling in your tools directly. The `computer` tool implementation in this project demonstrates how to scale both images and coordinates from higher resolutions to the suggested resolutions.

## Development

```bash
./setup.sh  # configure venv, install development dependencies, and install pre-commit hooks
docker build . -t computer-use-demo:local  # manually build the docker image (optional)
export ANTHROPIC_API_KEY=%your_api_key%
docker run \
    -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
    -v $(pwd)/computer_use_demo:/home/computeruse/computer_use_demo/ `# mount local python module for development` \
    -v $HOME/.anthropic:/home/computeruse/.anthropic \
    -p 5900:5900 \
    -p 8501:8501 \
    -p 6080:6080 \
    -p 8080:8080 \
    -it computer-use-demo:local  # can also use ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest
```

The docker run command above mounts the repo inside the docker image, such that you can edit files from the host. Streamlit is already configured with auto reloading.
