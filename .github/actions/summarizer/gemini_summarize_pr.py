"""Summarizes the pull request using the Gemini model and adds summary to a PR comment."""

# pylint: disable=line-too-long
import json
import os

from github import Github, PullRequest
import requests
import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel

GEMINI_MODEL = "gemini-1.5-flash-001"


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


def summarize_pr_gemini(
    pull_request_content: str,
    project_id: str,
    location: str = "us-central1",
    model_id: str = GEMINI_MODEL,
) -> str:
    """Calls the Gemini model to summarize the pull request content."""
    vertexai.init(project=project_id, location=location)

    model = GenerativeModel(
        model_id,
        system_instruction=[
            "You are an expert software engineer, proficient in Generative AI, Git and GitHub.",
        ],
        generation_config=GenerationConfig(temperature=0.0, max_output_tokens=8192),
    )

    prompt = [
        "The following is the content of a GitHub Pull Request for a repository focused on Generative AI with Google Cloud."
        "This content includes the Pull Request title, Pull Request description, "
        "a list of all of the files changed with the file name, the code diff and the raw file content."
        "Your task is to output a summary of the Pull Request in Markdown format.",
        "Content:",
        pull_request_content,
        "Summary:",
    ]

    print("---Prompt---\n", prompt)
    response = model.generate_content(prompt)
    print("---Gemini Response---\n", response)

    return response.text.replace("## Pull Request Summary", "")


def add_pr_comment(pr: PullRequest.PullRequest, summary: str) -> None:
    """Comments on the pull request with the provided summary."""
    comment_header = "## Pull Request Summary from [Gemini ✨](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/overview)"
    comment_body = f"{comment_header}\n{summary}\n---\nGenerated at `{pr.get_commits().reversed[0].sha}`"
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
    summary = summarize_pr_gemini(pr_content, os.getenv("GOOGLE_CLOUD_PROJECT_ID", ""))
    add_pr_comment(pr, summary)


if __name__ == "__main__":
    main()
