import os

import requests
import streamlit as st
import yaml

# Load configuration
config_path = os.environ.get(
    "CONFIG_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "common", "config.yaml"),
)
with open(config_path) as config_file:
    config = yaml.safe_load(config_file)

fastapi_url = config["fastapi_url"]

prompt_instructions = {
    "qa_prompt_tmpl": """This prompt instructs the LLM to convert a set of retrieved chunks for a given question into a natural language answer:\n
    context_str - the set of nodes retrieved from the retriever, concatenated as a string.\n
    query_str  - the query from the user""",
    "refine_prompt_tmpl": """This prompt instructs the LLM to refine an existing answer to a given question and given the context supplied by the retriever:\n
    existing_answer - the current answer to the query. \n
    context_msg - the set of nodes retrieved from the retriever, concatenated as a string. \n
    query_str - the query from the user""",
    "hyde_prompt_tmpl": """This prompt asks the LLM to hallucinate a response to the question.\n
    context_str - the query from the user""",
    "choice_select_prompt_tmpl": """This prompt instructs the LLM to re-rank a list of chunks by relevancy to the question.\n
    context_str - the list of nodes concatenated as a string\n
    query_str - the query from the user""",
    "system_prompt": """This is the overall system prompt passed to the LLM governing all retrieval steps above.""",
    "eval_prompt_wcontext_system": """This is the system prompt for the evaluator model to compute the Overall Score metric.""",
    "eval_prompt_wcontext_user": """This is the user prompt for the evaluator model to compute the Overall Score metric.""",
}


# Function to fetch all prompts
def fetch_prompts():
    response = requests.get(f"{fastapi_url}/get_all_prompts")
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch prompts. Please check the server connection.")
        return {}


# Function to update a single prompt
def update_prompt(prompt_name, new_content):
    response = requests.post(
        f"{fastapi_url}/update_prompt",
        json={"prompt_name": prompt_name, "new_content": new_content},
    )
    if response.status_code == 200:
        st.success(f"Prompt '{prompt_name}' updated successfully!")
    else:
        st.error(f"Failed to update prompt '{prompt_name}'. Please try again.")


st.title("Prompt Editor")

# Fetch current prompts
prompts = fetch_prompts()

# Display each prompt with an edit box and submit button
for prompt_name, prompt_content in prompts.items():
    st.subheader(prompt_name)
    new_content = st.text_area(
        prompt_instructions[prompt_name],
        value=prompt_content,
        height=200,
        key=prompt_name,
    )
    if st.button(f"Update {prompt_name}"):
        update_prompt(prompt_name, new_content)

# Button to refresh all prompts
if st.button("Refresh All Prompts"):
    st.experimental_rerun()
