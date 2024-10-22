"""
This module provides functions for rendering product feature drafts and
 managing user selections.
This module:
    * Fetches a product feature response from the LLM, ensuring a specific
      format.
    * Displays draft features in a grid layout with checkboxes for selection.
    * Facilitates the modification of selected features, updating the UI
      accordingly.
"""

import logging

from app.pages_utils.get_llm_response import generate_gemini
from dotenv import load_dotenv
import streamlit as st

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)

load_dotenv()

BOX_STYLE = """
    border: 0.5px solid #6a90e2;
    padding: 10px;
    margin: 10px;
    height: 280px;
    border-radius: 25px;
"""

CLICKED_BOX_STYLE = """
    border: 2px solid #3367D6;
    padding: 10px;
    margin: 10px;
    height: 280px;
    border-radius: 25px;
"""


def _add_title_to_selection(title: str) -> None:
    """Adds a title to the list of selected titles.

    Args:
        title (str): The title to add.
    """
    if title not in st.session_state.selected_titles:
        st.session_state.selected_titles.append(title)
        if st.session_state.modifying:
            st.rerun()


def _remove_title_from_selection(title: str) -> None:
    """Removes a title from the list of selected titles.

    Args:
        title (str): The title to remove.
    """
    if title in st.session_state.selected_titles:
        st.session_state.selected_titles.remove(title)


def _render_box(box_id: str, title: str, parts: list, class_name: str) -> None:
    """Renders a box with the given title, parts, and style.

    Args:
        box_id (str): The ID of the box.
        title (str): The title of the box.
        parts (list): The parts of the box.
        style (str): The style of the box.
    """
    st.markdown(
        f"""<div id={box_id} class={class_name}>
                <h5 style="color: #3367D6; text-align: center">
                    {title if len(parts) == 2 else parts[0]}
                </h5>
                <div> {'' if len(parts) == 0 else parts[1]} </div>
            </div>
        """,
        unsafe_allow_html=True,
    )


def get_features(text: str) -> list[str]:
    """Gets a list of features from the given text.
        App displays a grid of boxes where each box corresponds to
        a particular feature. This function divides the given input
        text to a list of those features

    Args:
        text (str): The text to get the points from.

    Returns:
        list: A list of points.
    """
    points = text.split("\n")
    curr = ""
    sep_points = []
    for point in points:
        point = point.strip()
        if point == "":
            continue
        if point.endswith(":"):
            curr = point
        else:
            if point.endswith("."):
                sep_points.append(curr.strip() + point.strip())
                curr = ""
            else:
                curr += point
    return sep_points


def generate_formatted_response(prompt: str) -> str:
    """Generates a formatted response based on the given prompt.

    Args:
        prompt (str): The user-selected or custom prompt.

    Returns:
        str: The formatted response text.
    """
    with st.spinner("Fetching Response..."):
        generated_response = generate_gemini(
            f""" {prompt} in 12 points. The answer should strictly
            be a numbered list. Every bullet point should be strictly
            less than 150 characters. Each point should strictly have
            the format of title followed by description separated by ':'.
            Every bullet point should strictly have exactly one title.
            Use of bold text should be avoided strictly.
            Each title should strictly be a combination of 2 or
            more features."""
        )
        formatted_response = generated_response.replace("**", "")
        logging.debug(formatted_response)
        return formatted_response


def render_features(features: st.delta_generator.DeltaGenerator) -> None:
    """Renders draft ideas in a grid format, allowing for selection.

    Args:
        features: A list of draft ideas to display.
    """

    if st.session_state.generated_points is None:
        st.session_state.generated_points = get_features(
            st.session_state.generated_response
        )

    with features:
        col1, col2, col3 = st.columns(3)

        for i, point in enumerate(st.session_state.generated_points):
            box = (
                col1 if i % 3 == 0 else col2 if i % 3 == 1 else col3
            )  # Inline conditionals

            box_id = f"box_{i}"

            # Split point into two parts based on a colon (':') delimiter
            parts = point.split(":", 1)  # Split at most once
            if len(parts) == 2:
                # Extract and clean up the parts
                first_part = parts[0].strip()
                second_part = parts[1].strip()
                parts = [first_part, second_part]
            # No colon found, part assigned as the whole sentence
            else:
                parts = [point]

            # Trim title to only the heading
            title = parts[0]
            try:
                title_parts = title.split(".")
                title = title_parts[1].strip()
            except IndexError:
                logging.debug("Unable to trim title")

            with box:
                checkbox_key = f"{title} {i}"

                # Checkbox logic for idea selection
                checkbox = st.checkbox(
                    "Select Idea",
                    key=checkbox_key,
                    value=title in st.session_state.selected_titles,
                )
                if checkbox:
                    _add_title_to_selection(title)
                else:
                    _remove_title_from_selection(title)

                # Rendering with appropriate styles
                if title in st.session_state.selected_titles:
                    _render_box(box_id, title, parts, "box-clicked")
                else:
                    _render_box(box_id, title, parts, "box-default")


def modify_selection(content: st.container) -> None:
    """Modifies the selection of features.

    Args:
        content: The streamlit container widget to modify.
    """
    st.session_state.modifying = True
    new_features = st.empty()
    render_features(new_features)
    if st.session_state.content_generated is True:
        content.empty()
        content = st.empty()
        st.session_state.content_generated = False
        st.session_state.product_content = []
        st.session_state.create_product = False
        st.session_state.generate_images = False
    st.rerun()
