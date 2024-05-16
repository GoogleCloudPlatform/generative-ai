"""
This module  provides functions for generating and managing product
content based on selected features.
Functions include:

    * Initiate text and image generation with user-provided features.
    * Store the generated content for display.
    * Support content generation with asynchronous calls.
    * Render a form for selecting pre-defined prompts or entering custom
      queries.
    * Facilitate the generation of product feature suggestions.
"""

import asyncio
import logging
from typing import Any

from app.pages_utils.get_llm_response import (
    generate_gemini,
    parallel_generate_search_results,
)
from app.pages_utils.imagen import parallel_image_generation
from dotenv import load_dotenv
import streamlit as st

logging.basicConfig(
    format="%(levelname)s:%(message)s",
    level=logging.DEBUG,
)
load_dotenv()


def update_generation_state() -> None:
    """Updates the generation state post generate button click."""

    # Check whether custom prompt has been given.
    if st.session_state.custom_prompt != "":
        st.session_state.selected_prompt = st.session_state.custom_prompt
        st.session_state.custom_prompt = ""

    st.session_state.features_generated = True  # Initiate feature generation
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
    st.session_state.product_content = []  # Content corresponding to each feature.
    st.session_state.content_edited = False  # Tracks whether content is being edited.


def generate_product_suggestions_for_feature_generation() -> None:
    """Generates suggestions for a given product category for feature
      generation.

    Returns:
        list: A list of feature suggestions.
    """
    with st.spinner("Fetching Suggestions..."):
        feature_prompts = generate_gemini(
            f"""5 broad categories of {st.session_state.product_category}
            buyers. Give answer as a numbered list. Each point should
            strictly be only a category without any description."""
        )
        st.session_state.feature_suggestions = create_suggestion_list(feature_prompts)


def build_prompt_form() -> bool:
    """Creates the form for selecting prompts and entering custom queries.

    Returns:
        Boolean value indicating whether the form was submitted.
    """
    if st.session_state.feature_suggestions is None:
        st.session_state.feature_suggestions = []
        generate_product_suggestions_for_feature_generation()
    with st.form("prompt input"):
        options = [
            f"""Recommend {st.session_state.product_category} formulation
            features for {segment}"""
            for segment in st.session_state.feature_suggestions
            if st.session_state.feature_suggestions is not None
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


def create_suggestion_list(gen_suggestions: str) -> list[str]:
    """Creates a list of suggestions from the generated suggestions.

    Args:
        gen_suggestions (str): The generated suggestions.

    Returns:
        list: A list of suggestions.
    """
    suggestions = []
    sep_suggestions = gen_suggestions.split("\n")
    for suggestion in sep_suggestions:
        suggestion_split = suggestion.split(".")
        if len(suggestion_split) > 1:
            suggestions.append(suggestion.split(".", 1)[1])

    return suggestions


async def parallel_call(titles: list[str]) -> list[Any]:
    """
    Performs parallel calls to the text and image generation APIs.

    Args:
        titles (list): A list of product titles.

    Returns:
        list: A list of tuples containing the text and image generation
          results.
    """
    logging.debug("entered parallel call")
    text_processes = []
    img_processes = []
    for index, title in enumerate(titles):
        # Handle edge case (No assorted products to be created in case only
        # one feature is selected)
        if index == 1 and len(st.session_state.selected_titles) == 1:
            break

        # Create image generation and text generation prompts.
        img_prompt = f"{st.session_state.product_category} with {title} packaging."
        text_prompt = f"""Generate an innovative and original idea for a
        {st.session_state.product_category} that is {title} for
        {st.session_state.selected_prompt}. List ingredients of the suggested
        product. List benefits for different demographics of consumers of the
        product. The answer should strictly be very long and detailed and
        capture all features of the suggested product. Separately give the
        utility of the product for any three example consumer segments.
        Strictly demonstrate how the suggested product is an improvement
        over existing products."""

        # Parallel calls to generate new content.
        if st.session_state.content_generated is False:
            text_processes.append(
                asyncio.create_task(parallel_generate_search_results(text_prompt))
            )
            img_processes.append(
                asyncio.create_task(parallel_image_generation(img_prompt, index))
            )

    # Append the generated content to final result arrays.
    text_result_arr = await asyncio.gather(*text_processes)
    image_result_arr = await asyncio.gather(*img_processes)

    return [text_result_arr, image_result_arr]


async def prepare_titles() -> list[str]:
    """Processes selected titles, handling edge cases.

    Returns:
        list: A list of processed titles.
    """
    titles = st.session_state.selected_titles.copy()

    # Assorted titles to be created only if the length of selected features
    # is greater than 1.
    if len(st.session_state.selected_titles) > 1:
        # Create assorted product title if end of array is reached.
        # If end of array selected_titles array is not reached, keep original
        # title.
        assorted_title = ", ".join(st.session_state.selected_titles)

        titles.append(assorted_title)
        # Store assorted title in session state.
        st.session_state.assorted_prod_title = assorted_title

    return titles


async def generate_product_content() -> None:
    """
    Generates product content based on the selected titles and prompts.
    """

    if st.session_state.product_content is None:
        st.session_state.product_content = []  # Initialize product content storage

    elements: list[list[dict[str, Any]]] = []

    with st.spinner("Generating Product Ideas.."):
        # Fetch appropriate titles for processing
        titles = await prepare_titles()

        # Call image and text generation function in parallel for efficiency
        task1 = asyncio.create_task(parallel_call(titles))
        result_array = await task1
        text_result_arr = result_array[0]

        # Iterate over selected titles to generate content
        i = 0
        while i <= len(st.session_state.selected_titles):
            if i == 1 and len(st.session_state.selected_titles) == 1:
                break

            # Prepare containers for the current iteration's content
            current_content = []

            # Representing elements as a list of lists to handle multiple
            # drafts for same feature.
            elements.append([])

            if i < len(st.session_state.selected_titles):
                title = titles[i]

            # Generate content only if not already generated
            if st.session_state.content_generated is False:
                if i < len(st.session_state.selected_titles):
                    current_content.append(text_result_arr[i])
                    st.session_state.product_content.append(current_content)
                else:
                    st.session_state.assorted_prod_content.append(text_result_arr[i])

                # Build data for display elements
                elements[i].append(
                    {
                        "title": f"{title.strip()}",
                        "text": (
                            st.session_state.product_content[i][0].strip()
                            if i < len(st.session_state.product_content)
                            else st.session_state.assorted_prod_content[0]
                        ),
                        "interval": None,
                        "img": f"gen_image{st.session_state.num_drafts*i+1}.png",
                    }
                )
                i += 1

    # Store elements for display purposes
    st.session_state.draft_elements = elements


async def handle_content_generation(features: st.container) -> None:
    """
    Encapsulates the core content generation process.

    Args:
        features (streamlit.container): A container to be cleared after
        content generation.
    """

    if not st.session_state.selected_titles:
        st.error("Please Select at least one Draft for Content Generation")
        return  # Stop execution if no titles are selected

    # features' is a UI element to be cleared
    features.empty()

    await generate_product_content()  # generates content

    st.session_state.create_product = (
        True  # Tracks whether product ideas have been generated.
    )
    st.session_state.content_generated = (
        True  # Tracks whether product content has been generated.
    )

    # Prepare titles for processing.
    st.session_state.chosen_titles = st.session_state.selected_titles.copy()
    if len(st.session_state.selected_titles) > 1:
        st.session_state.chosen_titles.append(st.session_state.assorted_prod_title)
