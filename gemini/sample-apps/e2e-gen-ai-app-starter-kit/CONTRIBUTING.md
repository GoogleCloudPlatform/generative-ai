# How to Contribute

We'd love to accept your patches and contributions to this sample. There are
just a few small guidelines you need to follow.

## Contributor License Agreement

Contributions to this project must be accompanied by a Contributor License Agreement. You (or your employer) retain the copyright to your contribution; this simply gives us permission to use and redistribute your contributions as part of the project. Head over to [Google Developers CLA](https://cla.developers.google.com/) to see your current agreements on file or to sign a new one.

You generally only need to submit a CLA once, so if you've already submitted one (even if it was for a different project), you probably don't need to do it again.

## Community Guidelines, Code Reviews, Contributor Guide

Please refer to the [root repository CONTRIBUTING.md file](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/CONTRIBUTING.md) for Community Guidelines, Code Reviews, Contributor Guide, or specific guidance for Google Employees.

## Code Quality Checks

To ensure code quality, we utilize automated checks. Before submitting a pull request, please run the following commands locally:

```bash
poetry install --with streamlit,jupyter,lint
```

This installs development dependencies, including linting tools.

Then, execute the following Makefile targets:

```bash
make lint
```

This command runs the following linters to check for code style, potential errors, and type hints:

- **codespell**: Detects common spelling mistakes in code and documentation.
- **ruff**: A fast linter that combines the functionality of several popular tools like flake8, isort, pycodestyle, and others.
- **mypy**: Performs static type checking to catch type errors before runtime.

```bash
make test
```

This command runs the test suite using pytest, covering both unit and integration tests:

- **`poetry run pytest tests/unit`**: Executes unit tests located in the `tests/unit` directory.
- **`poetry run pytest tests/integration`**: Executes integration tests located in the `tests/integration` directory.

Your pull request will also be automatically checked by these tools using GitHub Actions. Ensuring your code passes these checks locally will help expedite the review process.
