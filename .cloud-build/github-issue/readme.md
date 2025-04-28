# Create GitHub Issue on Notebook Test Failure

These Bash scripts installs GitHub CLI and automates the creation of a GitHub issue when automated notebook tests fail. It reads the error output from a specified file and uses the `gh` CLI to create a new issue in a designated repository.

## Purpose

The script aims to:

- Detect the presence of a failure file (`/workspace/Failure.txt`).
- If the file exists, create a GitHub issue with the file's content as the issue body.
- Include a predefined title, labels, and assignees in the issue.
- Provide informative messages about the success or failure of issue creation.

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated.
- A GitHub repository with write access for the user running the script.
- A failure file (`/workspace/Failure.txt`) containing the error output from failed notebook tests.

## Usage

1. **Save the script:** Save the provided script as `create_gh_issue.sh`.
2. **Set Repository Details:** Modify the variables `REPO_OWNER`, `REPO_NAME`, `ISSUE_ASSIGNEES` and `FAILURE_FILE` within the script to match your GitHub repository details and the location of the failure file.
3. **Add script to pipeline:**
