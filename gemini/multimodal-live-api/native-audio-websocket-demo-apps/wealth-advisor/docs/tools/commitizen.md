<!--
 Copyright 2025 Google LLC
 
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
 
     https://www.apache.org/licenses/LICENSE-2.0
 
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
-->

# Conventional Commits and Commitizen

This repository should aspire to use [Conventional Commits](https://www.conventionalcommits.org/) to standardize commit messages, making them more readable and facilitating automated tools like changelog generation. Commitizen is used as a tool to streamline the creation of commits that conform to this standard.

## Conventional Commits

Conventional Commits is a lightweight convention that defines a set of rules for creating an explicit commit history. A commit message should be structured as follows:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Common Types

*   **feat:** A new feature.
*   **fix:** A bug fix.
*   **docs:** Documentation only changes.
*   **style:** Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc.).
*   **refactor:** A code change that neither fixes a bug nor adds a feature.
*   **perf:** A code change that improves performance.
*   **test:** Adding missing tests or correcting existing tests.
*   **build:** Changes that affect the build system or external dependencies (example scopes: gulp, broccoli, npm).
*   **ci:** Changes to our CI configuration files and scripts (example scopes: Travis, Circle, BrowserStack, SauceLabs).
*   **chore** Changes made to internal tasks like updating build tools, dependencies, or configuration files.

### Scope

The scope is optional and provides additional contextual information, usually referring to the part of the codebase affected by the change (e.g., `feat(parser): ...`).

### Description

A very short description of the change.

### Body

A longer description of the change, providing more context.

### Footer

The footer can contain information about breaking changes and is also the place to reference GitHub issues that the commit closes. Breaking changes should start with the words `BREAKING CHANGE:` followed by a description of the change.

**Example:**

```
feat(api): add user profile endpoint

This commit introduces a new endpoint for retrieving user profiles.
It includes authentication and authorization checks.

BREAKING CHANGE: The API version has been bumped to 2.0 due to changes in the authentication flow.
Closes #123
```

## Commitizen

[Commitizen](https://commitizen-tools.github.io/commitizen/) is a command-line utility that helps in creating commit messages that follow the Conventional Commits standard. It prompts the user for the different parts of the commit message and generates the final message.

### Usage

1. **Stage your changes:**
    ```bash
    git add .
    ```

2. **Run Commitizen:**
    ```bash
    cz c
    ```

3. **Follow the prompts:** Commitizen will guide you through creating a commit message that conforms to the Conventional Commits specification.

### Benefits of Using Commitizen

*   **Consistency:** Ensures all commit messages adhere to the defined standard.
*   **Automation:** Facilitates automated changelog generation and release versioning.
*   **Readability:** Makes the commit history easier to read and understand.
*   **Reduced Errors:** Minimizes mistakes in commit message formatting.

By using Conventional Commits and Commitizen, we maintain a clean, consistent, and meaningful commit history, which improves collaboration and simplifies project management.
