"""
This module defines the 'ProductDrafts' class, responsible
for managing and displaying product content drafts.
"""

from app.pages_utils.get_llm_response import generate_gemini
import streamlit as st


class ProductDrafts:
    """
    Key functionalities include:

    * Draft Organization: Arranges drafts based on their associated product
      titles.
    * Display: Renders drafts in an expandable format, including both image
      and text components.
    * Edit Integration: Provides buttons to trigger image editing and text
      regeneration for each draft.
    """

    def __init__(self):
        # Initialize session state if needed
        if "create_product" not in st.session_state:
            st.session_state.create_product = False

    def display_drafts(self) -> None:
        """
        Displays all product drafts if the 'create_product' flag is True in
        session state.
        """

        if st.session_state.create_product:
            for i, chosen_title in enumerate(st.session_state.chosen_titles):
                # Create an expandable section for each product title
                with st.expander(chosen_title):
                    # Display a centered title heading
                    st.markdown(
                        f"""<h5 style = 'text-align: center; color: #6a90e2;'>
                            {chosen_title}
                        </h5>""",
                        unsafe_allow_html=True,
                    )

                    # Call the helper function to display drafts for this title
                    self.display_draft_row(i)

    def display_draft_row(self, title_index: int) -> None:
        """
        Displays a single row of drafts for a given product title.

        Args:
            title_index (int): The index of the product title in the
                            st.session_state.chosen_titles list.
        """

        for j in range(st.session_state.num_drafts):
            img_col, text_col = st.columns(2)  # Create two equal-width columns

            with img_col:
                # Display the image for the current draft
                st.image(st.session_state.draft_elements[title_index][j]["img"])

                # Call the function to handle image editing interactions
                self._handle_image_edit(title_index, j)

            with text_col:
                # Display the text for the current draft
                st.write(st.session_state.draft_elements[title_index][j]["text"])
                st.session_state.text_edit_prompt = st.text_input(
                    key="edit_text_prompt" + str(title_index) + str(j),
                    placeholder="Write a query to edit the text",
                    label="Write prompt to edit text",
                )
                if st.button(
                    "Regenerate",
                    key=f"""
                    edit text{st.session_state.chosen_titles[title_index]}
                     {st.session_state.num_drafts*title_index+j+1}
                    """,
                    type="primary",
                ):
                    # On button click begin content regeneration.
                    st.session_state.regenerate_btn = True
                    st.session_state.row = title_index  # Title number being edited.
                    # In case of multiple drafts, track the draft number
                    # being edited.
                    st.session_state.col = j
                    st.session_state.text_to_edit = st.session_state.draft_elements[
                        title_index
                    ][j][
                        "text"
                    ]  # Text content being edited.

                    # Update content
                    with st.spinner("Updating Content..."):
                        new_text_prompt = f"""Prompt: Based on the given query
                                            change the given context and give
                                            only the revised context.
                                            Query:
                                            {st.session_state.text_edit_prompt}
                                            Context:
                                            {st.session_state.text_to_edit} """
                        # Generate new text.
                        text = generate_gemini(new_text_prompt)
                        # Update text post text regeneration.
                        st.session_state.draft_elements[st.session_state.row][
                            st.session_state.col
                        ][
                            "text"
                        ] = text  # Update draft contents.
                        # Reset Text edit status to default.
                        st.session_state.text_edit_prompt = None
                        st.session_state.regenerate_btn = False
                        st.session_state.update_text_btn = None
                        # Reload page to display updated content
                        st.rerun()

    def _handle_image_edit(self, title_index: int, draft_index: int) -> None:
        """
        Handles image edit button interactions for a specific draft.

        Args:
            title_index (int): The index of the product title.
            draft_index (int): The index of the draft within the title.
        """

        # Construct a unique button key using title and draft index
        button_key = f"Edit Image - {title_index} - {draft_index}"

        if st.button("Edit Image", key=button_key, type="primary"):
            # Store information in session state to track which image is
            # being edited
            st.session_state.image_edit_row = title_index
            st.session_state.image_edit_col = draft_index

            # Calculate a unique index for the image and update the
            # session state.
            st.session_state.image_to_edit = (
                st.session_state.num_drafts * title_index + draft_index
            )
