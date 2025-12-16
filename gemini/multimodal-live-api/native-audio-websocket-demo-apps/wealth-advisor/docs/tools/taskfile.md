# Task

[Task](https://taskfile.dev) is a task runner/build tool that aims to be simpler and easier to use than, for example, GNU Make.

## Installation
To install the `task` binary, follow the instructions on the [Task site](https://taskfile.dev/installation/)  

_**Note:** If you are using the devcontainer, the `task` binary is already installed for you._


## Usage

This repository uses Task to simplify development workflows. The main entrypoint is the `Taskfile.yaml` in the project root. This file includes other taskfiles from the `.task` directory as needed.

To see a list of available tasks, run:

```bash
task
```

### Authentication

The `.task/gcloud.yaml` file contains tasks related to Google Cloud authentication. For example, to authenticate with your user account and set the Application Default Credentials (ADC), run:

```bash
task gcloud:login
```

If you need to authenticate using a service account, you can use the `gcloud:login-sa` task. This will set the ADC to impersonate the specified service account. Before running this task, ensure that you have set the `GCP_SERVICE_ACCOUNT` variable in `taskfile.env`.


### Environment Variables

The `taskfile.env` file contains environment variables that are used by the tasks. It is important to note that this file should not contain any secrets. Secrets should be stored in a secure location, such as Google Cloud Secret Manager, and then loaded into the environment when needed. The `Taskfile.yaml` file contains an example of how to load secrets from Secret Manager in the commented-out `show-secret` task.

### Python Virtual Environments

The `Taskfile.yaml` file also includes tasks for managing Python virtual environments using `uv`. To create or sync your virtual environment, you can run:

```bash
task venv-sync
```

This will create or update the virtual environment based on the requirements defined in the `uv.lock` file.

### Running Tests

To run tests, you can use the `test` task:

```bash
task test
```

### Creating your own tasks
You can create your own complex tasks and can even pass in arguments. You can find details at [taskfile.dev/usage](https://taskfile.dev/usage/)