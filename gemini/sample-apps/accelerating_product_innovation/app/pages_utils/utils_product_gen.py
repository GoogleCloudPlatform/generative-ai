"""
This module  provides functions for generating and managing product
content based on selected features.
Functions include:

    * Initiate text and image generation with user-provided features.
    * Store the generated content for display.
    * Support content generation with asynchronous calls.
"""

import asyncio
import logging
import os

import streamlit as st
from dotenv import load_dotenv

from app.pages_utils.utils_get_llm_response import (
    parallel_generate_search_results,
)
from app.pages_utils.utils_imagen import (
    parallel_image_generation,
)

logging.basicConfig(
    format="%(levelname)s:%(message)s",
    level=logging.DEBUG,
)
load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")


async def parallel_call(title_arr):
    """
    Performs parallel calls to the text and image generation APIs.

    Args:
        title_arr (list): A list of product titles.

    Returns:
        list: A list of tuples containing the text and image generation results.
    """
    logging.debug("entered parallel call")
    text_processes = []
    img_processes = []
    for index, title in enumerate(title_arr):
        # Handle edge case (No assorted products to be created in case only one feature is selected)
        if index == 1 and len(st.session_state.selected_titles) == 1:
            break

        # Create image generation and text generation prompts.
        img_prompt = f"{st.session_state.product_category} with {title} packaging."
        text_prompt = f"""Generate an innovative and original idea for a
        {st.session_state.product_category} that is {title} for
        {st.session_state.selected_prompt}. List ingredients of the suggested product.
        List benefits for different demographics of consumers of the product.
        The answer should strictly be very long and detailed and capture all features of
        the suggested product. Separately give the utility of the product for any
        three example consumer segments. Strictly demonstrate how the suggested product is
        an improvement over existing products."""

        # Parallel calls to generate new content.
        if st.session_state.content_generated is False:
            text_processes.append(
                asyncio.create_task(
                    parallel_generate_search_results(text_prompt)
                )
            )
            img_processes.append(
                asyncio.create_task(
                    parallel_image_generation(img_prompt, index)
                )
            )

    # Append the generated content to final resul arrays.
    text_result_arr = await asyncio.gather(*text_processes)
    image_result_arr = await asyncio.gather(*img_processes)

    return [text_result_arr, image_result_arr]


async def prepare_titles():
    """Processes selected titles, handling edge cases.

    Returns:
        list: A list of processed titles.
    """
    title_arr = []
    i = 0
    while i <= len(st.session_state.selected_titles):
        # No assorted titles to be created if the length of selected features is 1.
        if i == 1 and len(st.session_state.selected_titles) == 1:
            break

        # Create assorted product title if end of array is reached.
        # If end of array selected_titles array is not reached, keep original title.
        title = (
            st.session_state.selected_titles[i]
            if i < len(st.session_state.selected_titles)
            else ", ".join(st.session_state.selected_titles)
        )
        title_arr.append(title)

        # Store assorted title in session state.
        st.session_state.assorted_prod_title = title
        i += 1

    return title_arr


async def generate_product_content():
    """
    Generates product content based on the selected titles and prompts.
    """

    if st.session_state.product_content is None:
        st.session_state.product_content = (
            []
        )  # Initialize product content storage

    elements = []

    with st.spinner("Generating Product Ideas.."):

        # Fetch appropriate titles for processing
        title_arr = await prepare_titles()

        # Call image and text generation function in parallel for efficiency
        task1 = asyncio.create_task(parallel_call(title_arr))
        result_array = await task1
        text_result_arr = result_array[0]

        # Iterate over selected titles to generate content
        i = 0
        while i <= len(st.session_state.selected_titles):
            if i == 1 and len(st.session_state.selected_titles) == 1:
                break

            # Prepare containers for the current iteration's content
            current_content = []

            # Representing elements as a list of lists to handle multiple drafts for same feature.
            elements.append([])

            if i < len(st.session_state.selected_titles):
                title = title_arr[i]

            # Generate content only if not already generated
            if st.session_state.content_generated is False:

                if i < len(st.session_state.selected_titles):
                    current_content.append(text_result_arr[i])
                    st.session_state.product_content.append(
                        current_content
                    )
                else:
                    st.session_state.assorted_prod_content.append(
                        text_result_arr[i]
                    )

                # Build data for display elements
                elements[i].append(
                    dict(
                        title=f"{title.strip()}",
                        text=(
                            st.session_state.product_content[i][
                                0
                            ].strip()
                            if i
                            < len(st.session_state.product_content)
                            else st.session_state.assorted_prod_content[
                                0
                            ]
                        ),
                        interval=None,
                        img=f"./gen_image{st.session_state.num_drafts*i+1}.png",
                    ),
                )
                i += 1

    # Store elements for display purposes
    st.session_state.draft_elements = elements


async def render_content(features):
    """
    Handles button clicks and content generation logic.

    Args:
        features (streamlit.container): A container to be cleared after content generation.
    """

    if st.button("Generate Content", type="primary"):
        await handle_content_generation(features)


async def handle_content_generation(features):
    """
    Encapsulates the core content generation process.

    Args:
        features (streamlit.container): A container to be cleared after content generation.
    """

    if not st.session_state.selected_titles:
        st.error(
            "Please Select at least one Draft for Content Generation"
        )
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
    st.session_state.chosen_titles = (
        st.session_state.selected_titles.copy()
    )
    if len(st.session_state.selected_titles) > 1:
        st.session_state.chosen_titles.append(
            st.session_state.assorted_prod_title
        )
