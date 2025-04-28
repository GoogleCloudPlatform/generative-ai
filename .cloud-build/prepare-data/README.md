# check_and_comment.sh

This script is a Bash script designed to scan Jupyter Notebook files (`.ipynb`) within a specific directory and comment out a particular keyword if found.

## Purpose

The script searches for the keyword `app.kernel.do_shutdown` within all `.ipynb` files located in the `/workspace/generative-ai/gemini/getting-started/` directory. If the keyword is found, the script comments it out by adding a `#` at the beginning of the line.

This is often useful for disabling specific functionalities in Jupyter Notebooks without deleting the code, allowing for easy reversions.

## Usage

1. **Save the script:** Save the provided script as `check_and_comment.sh`.
2. **add script to step in pipeline:**
