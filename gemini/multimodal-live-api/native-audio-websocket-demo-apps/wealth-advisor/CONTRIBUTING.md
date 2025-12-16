# Contributing to AI Wealth Advisor

First off, thank you for considering contributing to AI Wealth Advisor! All contributions are welcome, including issues, new features, documentation, and bug fixes.

## Table of Contents
- [Contributing to AI Wealth Advisor](#contributing-to-ai-wealth-advisor)
  - [Table of Contents](#table-of-contents)
  - [Getting Started](#getting-started)
  - [Branching Strategy](#branching-strategy)
    - [Branch Naming Convention](#branch-naming-convention)
    - [Protected Branches](#protected-branches)
  - [Commit Message Guidelines](#commit-message-guidelines)
  - [Submitting Changes](#submitting-changes)
  - [Code Review Process](#code-review-process)

## Getting Started

1.  Fork the repository on GitLab.
    Clone your fork locally: `git clone git@gitlab.com:google-cloud-ce/communities/genai-fsa/northam/expert_requests/ai-wealth-advisor.git`
3.  Set up your development environment. AI Wealth Advisor uses devcontainers. Make sure all dependencies have been installed and everything is operating normally.

## Branching Strategy

We use a feature-based branching strategy. All new work should be done in a feature branch.

### Branch Naming Convention

To maintain a clean and organized repository, please follow this branch naming convention:

`<type>/<short-description>`

-   **type**:
    -   `feature`: For new features.
    -   `fix`: For bug fixes.
    -   `docs`: For documentation changes.
    -   `style`: For code style changes (formatting, etc.).
    -   `refactor`: For code refactoring.
    -   `test`: For adding or improving tests.
    -   `chore`: For maintenance tasks.

-   **short-description**: A few words describing the change, separated by hyphens.

**Examples:**
-   `feature/add-user-authentication`
-   `fix/resolve-login-issue`
-   `docs/update-contributing-guide`

### Protected Branches

The `main` and `dev` branches are protected. Direct pushes to these branches are not allowed. All changes must be submitted through a Merge Request from a feature branch.

-   **main**: Represents the production-ready code.
-   **dev**: Represents the latest development changes. All feature branches should be based on `dev`.

## Commit Message Guidelines

We use [Conventional Commits](https://www.conventionalcommits.org/) for our commit messages. This allows for automated changelog generation and makes the commit history easier to read.

To enforce this, we use [Commitizen](http://commitizen.github.io/cz-cli/). Please use it for your commits.

Instead of `git commit`, use the following command:

```shell
cz c
```

This will launch an interactive prompt that will guide you through creating a compliant commit message.

## Submitting Changes

1.  Create a new feature branch from `dev`.
2.  Make your changes and commit them using `cz c`.
3.  Push your branch to your fork: `git push origin <branch-name>`
4.  Open a Merge Request from your branch to the `dev` branch of the main repository.
5.  Fill out the Merge Request template with a clear description of your changes.

## Code Review Process

-   All Merge Requests will be reviewed by at least one maintainer.
-   Once your Merge Request is approved, it will be merged into the `dev` branch.

Thank you for your contribution!