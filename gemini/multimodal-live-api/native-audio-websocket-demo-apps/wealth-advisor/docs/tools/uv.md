# Using `uv` for Python package management
This project utilizes `uv` as a fast Python package installer and resolver, designed as a drop-in replacement for `pip`, `pip-tools`, `pyenv`, `pipx`, and more.

## What is `uv`?  
`uv` is a new tool built in Rust aimed at significantly speeding up Python package management. It offers the following advantages:
*   **Blazing Fast:** `uv` is orders of magnitude faster than `pip` and `pip-tools` when installing and resolving dependencies.
*   **Drop-in Replacement:**  It's designed to be compatible with existing workflows that use `pip`, making it easy to switch.
*   **Global Cache:** `uv` uses a global cache to avoid unnecessary downloads and installations of the same package versions across multiple projects.
*   **Adheres to [PEP 621][pep-621]:** Follows Python standards for storing project metadata better than alternatives such as `poetry`

## Installing `uv`

If you are using the [devcontainer](devcontainer.md), `uv` is already installed. Otherwise, you can find platform specific installation steps at [docs.astral.sh/uv/getting-started/installation/][installation]

## Managing Packages
___Installing Packages___  
To install a new python package (e.g. fastapi), run:
> ```sh
> uv add fastapi
>```

___Uninstalling Packages___  
To uninstall a package, run:
>```sh
> uv remove fastapi
>```

___Install Development Only Packages___  
To install a package only for development or testing, you can add a `--dev` flag:
> ```sh
> uv add --dev pytest fastapi
>```

You can also create arbitrary groups, such as "test"
> ```sh
> uv add --group test pytest
>```

## Running Commands
With `uv` there is no need to activate your virtual environment (although, VSCode might automatically do it for you).

Instead, you can run: 
>`$ uv run main.py`  
>`$ uv run uvicorn ...` 

This will invoke the command in the current virtual environment. ___Note:___ _when using `uv run`, you can skip adding `python` to get the script to run._ 

[pep-621]: https://peps.python.org/pep-0621/
[installation]: https://docs.astral.sh/uv/getting-started/installation/#installing-uv