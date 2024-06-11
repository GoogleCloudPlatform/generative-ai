import json
import os

from github import Github
import requests
import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel


def get_pr_number() -> str:
    event_path = os.getenv("GITHUB_EVENT_PATH", "")

    # Load event data
    with open(event_path, "r", encoding="utf-8") as f:
        event_data = json.load(f)

    # Determine the PR number based on the event
    if "pull_request" in event_data:
        return event_data["pull_request"]["number"]

    if (
        "issue" in event_data and "pull_request" in event_data["issue"]
    ):  # For comment events on PRs
        return event_data["issue"]["number"]

    raise ValueError("Unable to determine pull request number from event data.")


def call_gemini(
    pull_request_content: str, model_id: str = "gemini-1.5-flash-001"
) -> str:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    vertexai.init(project=project_id, location="us-central1")

    model = GenerativeModel(
        model_id,
        system_instruction=[
            "You are an expert software engineer.",
        ],
        generation_config=GenerationConfig(temperature=0.0),
    )

    prompt = [
        "The following is the content of a GitHub Pull Request for a repository focused on Generative AI with Google Cloud. This content includes the Pull Request title, Pull Request description, a list of all of the files changed with the file name, the code diff and the raw file content. Your task is to output a summary of the Pull Request in Markdown format.",
        "Content:",
        pull_request_content,
        "Summary:",
    ]

    print("---Prompt---\n", prompt)
    response = model.generate_content(prompt)
    print("---Gemini Response---\n", response)

    return response.text.replace("## Pull Request Summary", "")


def summarize_pr(token, repo_name, pr_number):
    """Summarizes the pull request using the Gemini model and updates/creates a comment."""
    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

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
                raw_content = requests.get(file.raw_url).text
                pr_content += f"Raw File Content:\n`\n{raw_content}\n`\n\n"
            except requests.exceptions.RequestException:
                pr_content += "Unable to fetch raw file content.\n\n"
        else:  # Use patch if available
            pr_content += f"Code Diff:\n{file.patch}\n\n"

    summary = call_gemini(pr_content)

    comment_header = "## Pull Request Summary from [Gemini ✨](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/overview)"
    comment_body = (
        f"{comment_header}\n{summary}\n---\nGenerated at `{pr.get_commits()[0].sha}`"
    )
    bot_username = "github-actions[bot]"

    # Find and update existing bot comment if any
    for comment in pr.get_issue_comments():
        if comment.user.login == bot_username and comment_header in comment.body:
            comment.edit(comment_body)
            return

    # Create a new comment if none exists
    pr.create_issue_comment(comment_body)


def main():
    # Get GitHub token and repository details
    repo_name = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    pr_number = get_pr_number()

    summarize_pr(token, repo_name, pr_number)


if __name__ == "__main__":
    main()
