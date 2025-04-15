# 00 Metadata Generator

In this application Google Cloud **Gemini** model is used to generate *Big Query* Tables metadata such as tags, policy tags and descriptions in order to enhance data governance, improve searchability, and provide richer context for analysts and engineers. The generated metadata helps standardize documentation, enforce access policies, and streamline data management within BigQuery.

## Repository Structure

This section describes the structure of the repository and the purpose of each directory and file.

## Root Directory
* **pyproject.toml** - Python project configuration file.
* **README.md** - Project documentation (this file).

### src/

Contains the main source code of the project, organized into modules.

* **config.ini** - Configuration file for global settings.
* **utils.py** - Contains utils functions.
* **main.py** - entry point.

### src/agents/
* **notes_agent.py** - Contains logic for handling note-related agents.

### src/data/
* **metadata_example.py** - Contains an example for the few-shot prompt

### src/dependencies/
* **bq.py** - Big Query client class

### src/models/
* **metadata_model.py** - Contains models for handling metadata generation.




### Summary

This modular structure ensures the project is organized, scalable, and easy to maintain. Each component is placed in its relevant directory to promote clean code practices and separation of concerns.

<br>

---

<br><br>

# Setup
This application leverages the Google Cloud Gemini model. To use this LLM, ensure you have the following:

* *Enable* Vertex AI in your Google Cloud project.
* *Create* a Service Account (with VertexAI Admin permissions for semplicity)
* *Add* new SA API Key, download and save creds.json key and put in **/agents** folder


<br>

# Local Installation and Run
Create Virtual Environment in `/gemini-bq-metadata-gen`
```bash
virtualenv .venv -p python3.12
```
Activate Virtual Environment
```bash
source .venv/bin/activate
```
Install packages
```bash
pip install -e .
```
### Usage
Run Application
```bash
 python src/main.py
```
