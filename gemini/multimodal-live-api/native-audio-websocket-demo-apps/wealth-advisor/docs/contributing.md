# Contributing to AI Wealth Advisor

We'd love to accept your patches and contributions to this project! This guide will walk you through the process.

## 🤝 Prerequisites

1.  **Google Contributor License Agreement (CLA):**
    Contributions must be accompanied by a signed CLA. You (or your employer) retain copyright, but this gives us permission to use your code.
    *   **Sign here:** <https://cla.developers.google.com/>
    *   *Note: You generally only need to do this once.*

## 💻 Development Workflow

### 1. Fork & Clone
Fork the repository to your own account and clone it locally.
```bash
git clone <your-fork-url>
cd citi-wealth-advisor
```

### 2. Create a Feature Branch
All work should be done in a specific feature branch, not directly on `main`.
```bash
git checkout -b feature/my-new-feature
```

### 3. Setup Environment
Ensure your development environment is set up according to [docs/setup.md](docs/setup.md).
```bash
# Verify basic tools
uv --version
npm --version
```

### 4. Make Changes & Test
Implement your feature or fix.
*   **Frontend:** Run `npm run dev` to test locally.
*   **Backend:** Run `uv run uvicorn api.main:app` to test locally.

### 5. Lint & Format
Before submitting, run the project's quality checks.
```bash
# Backend (Python)
uv run ruff check .
uv run ruff format .

# Frontend (TypeScript)
cd src/frontend
npm run lint
```
*   **Jupyter Notebooks:** If you modify `.ipynb` files, format them:
    ```bash
    python3 -m pip install --upgrade nox
    nox -s format
    ```

## 📝 Submitting a Pull Request

1.  **Commit:** Write clear, concise commit messages.
    ```bash
    git commit -m "feat: Add new market analysis tool"
    ```
2.  **Push:** Push your branch to your fork.
    ```bash
    git push origin feature/my-new-feature
    ```
3.  **Open PR:** Go to the official repository and open a Pull Request targeting the `main` branch.

### Review Checklist
*   [ ] Signed the CLA.
*   [ ] Ran `uv run ruff check` and passed.
*   [ ] Ran `npm run lint` and passed.
*   [ ] Verified no new errors in logs.

## 📜 Community Guidelines
This project follows [Google's Open Source Community Guidelines](https://opensource.google/conduct/). Please be respectful and constructive.
