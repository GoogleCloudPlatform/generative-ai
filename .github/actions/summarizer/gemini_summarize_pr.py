"""Summarizes the pull request using the Gemini model and adds summary to a PR comment."""

# pylint: disable=line-too-long,too-many-arguments
from datetime import datetime
import json
import os
from typing import Optional, Sequence, Tuple

from github import Github, PullRequest
from google.cloud import bigquery, storage
import requests
import vertexai
from vertexai.generative_models import (
    GenerationConfig,
    GenerationResponse,
    GenerativeModel,
)


def get_pr_number(event_path: str) -> int:
    """Retrieves the pull request number from GitHub event data."""
    # Load event data
    with open(event_path, "r", encoding="utf-8") as f:
        event_data = json.load(f)

    # Determine the PR number based on the event
    if "pull_request" in event_data:
        return int(event_data["pull_request"]["number"])

    if (
        "issue" in event_data and "pull_request" in event_data["issue"]
    ):  # For comment events on PRs
        return int(event_data["issue"]["number"])

    raise ValueError("Unable to determine pull request number from event data.")


def get_pr_content(pr: PullRequest.PullRequest) -> str:
    """Returns the content of the pull request as a string."""
    pr_content = f"""
    Title: {pr.title}
    Pull Request Description: {pr.body}

    --- Files Changed ---
    """

    for file in pr.get_files():
        pr_content += f"File name: {file.filename}\n\n"

        # Attempt to fetch raw content if patch is not available
        if file.patch is None:
            try:
                raw_content = requests.get(file.raw_url, timeout=10).text
                pr_content += f"Raw File Content:\n`\n{raw_content}\n`\n\n"
            except requests.exceptions.RequestException:
                pr_content += "Unable to fetch raw file content.\n\n"
        else:  # Use patch if available
            pr_content += f"Code Diff:\n{file.patch}\n\n"

    return pr_content


def log_prompt_to_bigquery(
    pr_number: int,
    commit_id: str,
    input_prompt: str,
    model_output: Optional[str],
    raw_response: GenerationResponse,
    model_name: str,
) -> Sequence[dict]:
    """Log Gemini prompt input/output to BigQuery."""
    client = bigquery.Client()
    table_id = os.getenv("BIGQUERY_SUMMARIZE_LOGS_TABLE", "")

    rows_to_insert = [
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pr_number": pr_number,
            "commit_id": commit_id,
            "input_prompt": input_prompt,
            "model_output": model_output,
            "raw_response_str": repr(raw_response.to_dict()),
            "model": model_name,
        }
    ]
    return client.insert_rows_json(table_id, rows_to_insert)


def summarize_pr_gemini(
    pull_request_content: str,
    project_id: str,
    prompt_file_uri: str,
    location: str = "us-central1",
) -> Tuple[Optional[str], str, GenerationResponse, str]:
    """Calls the Gemini model to summarize the pull request content."""
    vertexai.init(project=project_id, location=location)

    blob = storage.Blob.from_string(prompt_file_uri, client=storage.Client())
    prompt = json.loads(blob.download_as_text())

    model_name = prompt["model"]
    model = GenerativeModel(
        model_name,
        system_instruction=[prompt["system_instruction"]],
        generation_config=GenerationConfig(
            temperature=prompt["temperature"],
            max_output_tokens=prompt["max_output_tokens"],
        ),
    )

    input_prompt = prompt["prompt"].format(pull_request_content=pull_request_content)

    response = model.generate_content(input_prompt)
    try:
        output_text = response.text.replace("## Pull Request Summary", "")
    except Exception:  # pylint: disable=broad-exception-caught
        output_text = None

    return (output_text, input_prompt, response, model_name)


def add_pr_comment(pr: PullRequest.PullRequest, summary: str, commit_id: str) -> None:
    """Comments on the pull request with the provided summary."""
    comment_header = "## Pull Request Summary from [Gemini ✨](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/overview)"
    comment_body = f"{comment_header}\n{summary}\n---\nGenerated at `{commit_id}`"
    bot_username = "github-actions[bot]"

    # Find and update existing bot comment if any
    for comment in pr.get_issue_comments():
        if comment.user.login == bot_username and comment_header in comment.body:
            comment.edit(comment_body)
            return

    # Create a new comment if none exists
    pr.create_issue_comment(comment_body)


def main() -> None:
    """Summarizes the pull request using the Gemini model and adds summary to a PR comment."""

    # Get GitHub token and repository details
    repo_name = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN")
    pr_number = get_pr_number(os.getenv("GITHUB_EVENT_PATH", ""))

    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    pr_content = get_pr_content(pr)
    summary, input_prompt, raw_response, model_name = summarize_pr_gemini(
        pr_content,
        os.getenv("GOOGLE_CLOUD_PROJECT_ID", ""),
        # See example_prompt.json for an example prompt.
        os.getenv("PROMPT_FILE", ""),
    )

    commit_id = pr.get_commits().reversed[0].sha

    bq_output = log_prompt_to_bigquery(
        pr_number, commit_id, input_prompt, summary, raw_response, model_name
    )
    print(bq_output)

    if summary:
        add_pr_comment(pr, summary, commit_id)


if __name__ == "__main__":
    main()
