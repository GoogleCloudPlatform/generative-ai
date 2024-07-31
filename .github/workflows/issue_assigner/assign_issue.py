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
    with open(event_path, "r", encoding="utf-8") as f:
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

    file_match = re.search(r"\b([\w-]+\.ipynb)\b", issue.body, re.IGNORECASE)

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
    print(result[0])
    file = str(base64.b64decode(result[0].content))[:4000]
    match = re.search(r"Author.+https://github\.com/([^/\)]+)", file)

    if not match:
        print(f"No User Found for {file_name}")
        return

    username = match.group(1)
    print(f"Assigning {username} to Issue #{issue_number} for File {result[0].path}")
    issue.add_to_assignees(username)


if __name__ == "__main__":
    main()
