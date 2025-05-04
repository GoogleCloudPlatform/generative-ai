## Setting up

Create a virtual environment on the root of the application and activate it.

```
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

### Running the set up script

```
python3 setup.py
```

### Running the application on local
Create a virtual environment, activate it, install the requirements, set environmental variables from local.env and run the application

```
. ./local.env
uvicorn main:app --reload --port 8080
```

## Code Styling & Commit Guidelines

To maintain code quality and consistency:

* **TypeScript (Frontend):** We follow [Angular Coding Style Guide](https://angular.dev/style-guide) by leveraging the use of [Google's TypeScript Style Guide](https://github.com/google/gts) using `gts`. This includes a formatter, linter, and automatic code fixer.
* **Python (Backend):** We adhere to the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), using tools like `pylint` and `black` for linting and formatting.
* **Commit Messages:** We suggest following [Angular's Commit Message Guidelines](https://github.com/angular/angular/blob/main/contributing-docs/commit-message-guidelines.md) to create clear and descriptive commit messages.

#### Frontend (TypeScript with `gts`)

1.  **Initialize `gts` (if not already done in the project):**
    Navigate to the `frontend/` directory and run:
    ```bash
    npx gts init
    ```
    This will set up `gts` and create necessary configuration files (like `tsconfig.json`). Ensure your `tsconfig.json` (or a related gts config file like `.gtsrc`) includes an extension for `gts` defaults, typically:
    ```json
    {
      "extends": "./node_modules/gts/tsconfig-google.json",
      // ... other configurations
    }
    ```
2.  **Check for linting issues:**
    ```bash
    npm run lint
    ```
    (This assumes a `lint` script is defined in `package.json`, e.g., `"lint": "gts lint"`)
3.  **Fix linting issues automatically (where possible):**
    ```bash
    npm run fix
    ```
    (This assumes a `fix` script is defined in `package.json`, e.g., `"fix": "gts fix"`)

#### Backend (Python with `pylint` and `black`)

1.  **Ensure Dependencies are Installed:**
    Add `pylint` and `black` to your `backend/requirements.txt` file:
    ```
    pylint
    black
    ```
    Then install them within your virtual environment:
    ```bash
    pip install pylint black
    # or pip install -r requirements.txt
    ```
2.  **Configure `pylint`:**
    It's recommended to have a `.pylintrc` file in your `backend/` directory to configure `pylint` rules. You might need to copy a standard one or generate one (`pylint --generate-rcfile > .pylintrc`).
3.  **Check for linting issues with `pylint`:**
    Navigate to the `backend/` directory and run:
    ```bash
    pylint .
    ```
    (Or specify modules/packages: `pylint your_module_name`)
4.  **Format code with `black`:**
    To automatically format all Python files in the current directory and subdirectories:
    ```bash
    python -m black . --line-length=80
    ```
