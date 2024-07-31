"""Assigns the issue based on who created the file mentioned."""

# pylint: disable=line-too-long,too-many-arguments
import base64
import os
import re

from github import Github


def main() -> None:
    # Get GitHub token and repository details
    repo_name = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN")
    issue_number = int(os.environ["GITHUB_EVENT_ISSUE_NUMBER"])

    g = Github(token)
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(number=issue_number)

    file_match = re.search(r"\b([\w-]+\.ipynb)\b", issue.body, re.IGNORECASE)

    if not file_match:
        print("No matching file found")
        return

    file_name = file_match.group(1)
    print(file_name)
    result = g.search_code(f"repo:{repo_name} filename:{file_name}")
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
