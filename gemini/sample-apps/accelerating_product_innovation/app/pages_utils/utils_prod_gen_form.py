"""
This module provides functions for managing the product feature generation process. 
Functions include:
    * Render a form for selecting pre-defined prompts or entering custom queries. 
    * Facilitate the generation of product feature suggestions.
"""

import streamlit as st
from app.pages_utils.utils_get_llm_response import (
    generate_gemini,
)


def update_generation_state():
    """Updates the generation state post generate button click."""

    # Check whether custom prompt has been given.
    if st.session_state.custom_prompt != "":
        st.session_state.selected_prompt = (
            st.session_state.custom_prompt
        )
        st.session_state.custom_prompt = ""

    st.session_state.features_generated = (
        True  # Initate feature generation
    )
    st.session_state.generated_response = (
        None  # store the response by llm for features.
    )
    # Track whether content corresponding to features has been generated.
    st.session_state.content_generated = False
    st.session_state.create_product = (
        False  # Tracks whether a new product idea has been created.
    )
    st.session_state.selected_titles = (
        []
    )  # Stores selected titles for new product generation.
    st.session_state.product_content = (
        []
    )  # Content corresponding to each feature.
    st.session_state.content_edited = (
        False  # Tracks whether content is being edited.
    )


def generate_product_suggestions_for_feature_generation():
    """Generates suggestions for a given product category for feature generation.

    Args:
        product_category (str): The category of the product.

    Returns:
        list: A list of feature suggestions.
    """
    with st.spinner("Fetching Suggestions..."):
        feature_prompts = generate_gemini(
            f"""5 broad categories of {st.session_state.product_category} buyers. 
            Give answer as a numbered list. Each point should strictly be only 
            a category without any description."""
        )
        st.session_state.feature_suggestions = create_suggestion_list(
            feature_prompts
        )


def build_prompt_form():
    """Creates the form for selecting prompts and entering custom queries."""
    if st.session_state.feature_suggestions is None:
        generate_product_suggestions_for_feature_generation()
    with st.form("prompt input"):
        options = [
            f"Recommend {st.session_state.product_category} formulation features for {segment}"
            for segment in st.session_state.feature_suggestions
        ]
        st.session_state.selected_prompt = st.selectbox(
            "Select an option or enter a custom query",
            options,
        )
        st.session_state.custom_prompt = st.text_input(
            "Enter your custom query",
            st.session_state.custom_prompt,
        )
        st.session_state.num_drafts = 1
        return st.form_submit_button("Generate", type="primary")


def create_suggestion_list(gen_suggestions):
    """Creates a list of suggestions from the generated suggestions.

    Args:
        gen_suggestions (str): The generated suggestions.

    Returns:
        list: A list of suggestions.
    """
    suggestions = []
    sep_suggestions = gen_suggestions.split("\n")
    for suggestion in sep_suggestions:
        sug = suggestion.split(".")
        if len(sug) > 1:
            suggestions.append(suggestion.split(".", 1)[1])

    return suggestions
