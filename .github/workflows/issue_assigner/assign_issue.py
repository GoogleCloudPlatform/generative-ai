"""Assigns the issue based on who created the file mentioned."""

# pylint: disable=line-too-long,too-many-arguments
import base64
import json
import os
import re

from github import Github


def get_issue_number(event_path: str) -> int:
    """Retrieves the issue number from GitHub event data."""
    # Load event data
    with open(event_path, encoding="utf-8") as f:
        event_data = json.load(f)

    # Determine the issue number based on the event
    if "issue" in event_data:
        return int(event_data["issue"]["number"])

    raise ValueError("Unable to determine issue number from event data.")


def main() -> None:
    """Gets filename mentioned in issue, finds author username in file, assigns issue to user."""
    # Get GitHub token and repository details
    repo_name = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN")
    issue_number = get_issue_number(os.getenv("GITHUB_EVENT_PATH", ""))

    g = Github(token)
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(number=issue_number)

    # Regex to find any file with an extension
    file_match = re.search(r"\b([\w-]+\.[\w]+)\b", issue.body, re.IGNORECASE)

    if not file_match:
        print("No file found in issue.")
        return

    file_name = file_match.group(1)
    result = g.search_code(f"repo:{repo_name} filename:{file_name}")

    if result.totalCount == 0:
        result = g.search_code(f"repo:{repo_name} {file_name}")
        if result.totalCount == 0:
            print(f"No files found for {file_name}")
            return

    file_path = result[0].path

    # Get the commits for the file
    commits = repo.get_commits(path=file_path)

    # Try to get the author of the first commit
    if commits.totalCount > 0:
        # The last commit in the list is the first commit
        first_commit = commits[commits.totalCount - 1]
        if first_commit.author:
            username = first_commit.author.login
            print(
                f"Assigning {username} to Issue #{issue_number} for File {file_path} based on the first commit."
            )
            issue.add_to_assignees(username)
            return

    # If the file is a notebook and the first commit author wasn't found,
    # check the notebook metadata as a fallback.
    if file_name.endswith(".ipynb"):
        print(
            "Could not determine the first commit author, checking the notebook metadata."
        )
        file_content_encoded = repo.get_contents(file_path).content
        file_content = str(base64.b64decode(file_content_encoded))[:10000]
        match = re.search(
            r"Author.+https://github\.com/([^/\)]+)", file_content, flags=re.DOTALL
        )

        if match:
            username = match.group(1)
            print(
                f"Assigning {username} to Issue #{issue_number} for File {file_path} based on notebook metadata."
            )
            issue.add_to_assignees(username)
            return

    print(f"No User Found for {file_name}")


if __name__ == "__main__":
    main()
