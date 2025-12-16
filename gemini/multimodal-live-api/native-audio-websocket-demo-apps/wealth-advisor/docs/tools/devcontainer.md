<!--
 Copyright 2025 Google LLC
 
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
 
     https://www.apache.org/licenses/LICENSE-2.0
 
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
-->


# Devcontainer

This project has a [devcontainer](https://containers.dev/) specified, which is an open specification for creating consistent development environments. An easy way to think of devcontainers are "Developer-VMs-as-Code".

## What are Devcontainers?

Devcontainers (Development Containers) provide a consistent and isolated development environment by leveraging containerization technology. They define the tools, runtimes, and dependencies required for a project within a Docker container, ensuring that all developers work within the same setup, regardless of their local operating system or configuration.

**Benefits of Using Devcontainers:**

*   **Consistency:** Eliminates the "works on my machine" problem by ensuring everyone uses the same environment.
*   **Isolation:** Dependencies and tools are contained within the container, preventing conflicts with your local system or other projects.
*   **Reproducibility:** The environment can be easily recreated on any system that supports Docker.
*   **Onboarding:** Simplifies onboarding for new team members as they can quickly get a working development environment.
*   **Version Control:** The devcontainer configuration is stored in the repository, allowing you to track changes to the development environment alongside your code.

## What's Inside This Devcontainer?

This project's devcontainer is defined by the files within the `.devcontainer` folder:

*   **`devcontainer.json`:** The main configuration file. It specifies:
    *   The base Docker image (Ubuntu 22.04 in this case).
    *   Build arguments like `VARIANT`, `UV_VERSION`, `ASDF_BRANCH`, and `TASK_VERSION`.
    *   VS Code extensions to be installed within the container (e.g., GitLens, Python, Docker, Terraform, Ruff, Prettier, etc.)
    *   "Features" such as common utilities and docker-in-docker support.
    *   `remoteUser` set to `vscode`.
    *   Post-creation commands to be executed (see `postCreate.sh`).
*   **`Dockerfile`:**  Describes how to build the Docker image for the devcontainer.
    *   Installs the [`task`](taskfile.md) task runner from a binary.
    *   Installs `asdf` (a version manager) from source
    *   Installs the `gcloud` CLI.
    *   Installs [`uv`](uv.md) (a python tool) from source.
*   **`postCreate.sh`:** A shell script executed after the container is created.
    *   Installs tools specified in `.tool-version` files using `asdf`.
        * This will install the `adr` cli since that is specified in the `.tool-versions` file
    *   Installs Python tools like [`ruff`](ruff.md), [`bandit`](https://bandit.readthedocs.io/en/latest/), and [`commitizen`](commitizen.md) using `uv tool install`.
    *   Sets up command completion for `asdf`, `task`, and `uv`.
    *   Sets the `PATH` variable to include shims from asdf

## Using Devcontainers with VS Code

Visual Studio Code has excellent support for devcontainers through the "Remote - Containers" extension. Here's how to use it:

1. **Install (or have access to) Docker:** Make sure you have Docker Desktop or a compatible Docker engine installed on your local machine, alternatively, you can first connect to a VM that has a compatible Docker engine installed using the "Remote - SSH" extension.
2. **Install the Extension:** Install the "Dev Containers" extension (formerly "Remote - Containers") in VS Code - and the "Remote - SSH" extension if needed.
3. **Open the Project:** Open the project folder in VS Code.
4. **Reopen in Container:**
    *   You should see a prompt to "Reopen in Container". Click it.
    *   Alternatively, open the Command Palette (F1 or Ctrl+Shift+P) and run the command "Dev Containers: Reopen in Container".
5. **Build and Run:** VS Code will build the Docker image (if it doesn't exist) and start the container. This might take some time initially.
6. **Develop:** Once the container is running, you'll be working inside the isolated environment. VS Code will automatically connect to the container, and your extensions, settings, and tools will be available as defined in `devcontainer.json`.

**Important Notes:**

*   Any changes you make to the files within the container are reflected in your local project folder because the project directory is mounted into the container.
*   When you close VS Code or stop the container, it will be shutdown due to the `shutdownAction` setting in `devcontainer.json`.

By using devcontainers, this project ensures a consistent, reproducible, and easy-to-use development environment for all contributors.
