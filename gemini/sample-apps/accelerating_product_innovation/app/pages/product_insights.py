"""
This module manages the 'Insights' page of the Streamlit application.
It provides the following functionality:

* Project Management: Displays currently selected project.
* Data Handling:
    * Checks for uploaded files in the specified project category.
    * Loads File Data (if uploaded files exist).
* Question & Answer (QA):
    * Offers suggested questions for insights (requires uploaded data)
      through Retrieval Augmented Generation.
    * Enables users to input their own questions.
    * Generates answers to questions based on uploaded data, including
      references.
* Follow-up Questions: Suggests follow-up questions based on previous queries.
"""

from app.pages_utils import insights, setup
from app.pages_utils.pages_config import PAGES_CFG
import streamlit as st

# Get page configuration from config file
page_cfg = PAGES_CFG["2_Marketing_Insights"]
setup.page_setup(page_cfg)

# Initialize temporary suggestions if not already initialized
if "temp_suggestions" not in st.session_state:
    st.session_state.temp_suggestions = None


# Cache the function to get insights images
@st.cache_data
def get_insights_img() -> None:
    """
    Loads, displays and cache header image for insights page.

    Returns:
        None
    """
    page_images = [page_cfg["prod_insights_1"], page_cfg["prod_insights_2"]]
    for page_image in page_images:
        st.image(page_image)
        st.divider()


# Display header images
get_insights_img()

# Display projects
setup.display_projects()

# Check if data frame is empty
if st.session_state.embeddings_df is None or st.session_state.embeddings_df.empty:
    with st.spinner("Fetching Uploaded Files..."):
        embeddings_df = insights.get_stored_embeddings_as_df()
        st.session_state.embeddings_df = embeddings_df


# Function to display suggestion box
def display_suggestion_box(key: str, suggestion_num: int) -> None:
    """
    Styles and displays the suggestion for insight generation.
    Args:
        key: Unique key for suggestion.
        suggestion_num: Current suggestion number.
    """
    # Apply custom styling to suggestion box
    setup.load_css("app/css/prod_insights_styles.css")
    # Display suggestion button
    if st.button(
        st.session_state.insights_suggestion[suggestion_num],
        key=key,
    ):
        # Update session state with selected suggestion
        st.session_state.insights_placeholder = st.session_state.insights_suggestion[
            suggestion_num
        ]
        # Set flag to generate RAG answers
        st.session_state.rag_answers_gen = True


# Display suggested questions
st.divider()
st.write("**SUGGESTED QUESTIONS:**")

# Check if data frame is empty
if st.session_state.embeddings_df is None or st.session_state.embeddings_df.empty:
    # Display error message
    st.error(
        "Add files in "
        + st.session_state.product_category
        + " file storage to get suggested questions",
        icon="🚨",
    )
else:
    # Loop until suggestions are loaded or try limit is reached
    for try_var in range(3):
        if (
            st.session_state.suggestion_first_time
            and st.session_state.insights_suggestion is None
        ):
            with st.spinner("Loading suggestion..."):
                insights.get_suggestions("insights_suggestion")
                # Check if number of suggestions is less than 4
                if (
                    st.session_state.insights_suggestion is not None
                    and len(st.session_state.insights_suggestion) < 4
                ):
                    insights.get_suggestions("insights_suggestion")

    # Check if suggestions are loaded
    if (
        st.session_state.insights_suggestion is None
        or len(st.session_state.insights_suggestion) < 4
    ):
        st.write(st.session_state.insights_suggestion)
        # Display error message
        st.error("Sorry couldn't load suggestion")
    else:
        # Clear previous suggestions
        st.empty()

        # Create columns for suggestion boxes
        suggestion_col1 = st.columns(2)

        # Display suggestion boxes in first column
        with suggestion_col1[0]:
            display_suggestion_box("001", 0)
        with suggestion_col1[1]:
            display_suggestion_box("002", 1)

        # Create columns for suggestion boxes
        suggestion_col2 = st.columns(2)

        # Display suggestion boxes in second column
        with suggestion_col2[0]:
            display_suggestion_box("003", 2)
        with suggestion_col2[1]:
            display_suggestion_box("004", 3)

# Display divider
st.divider()

# Get search term from text area
search_term = st.text_area(
    "",
    key="2",
    value=st.session_state.insights_placeholder,
    placeholder="Select a suggestion or type your question here",
)

# Display search button
if st.button("Search", type="primary"):
    # Set flag to generate RAG answers
    st.session_state.rag_answers_gen = True

# Check if RAG answers should be generated
if st.session_state.rag_answers_gen:
    # Check if data frame is empty
    if st.session_state.embeddings_df is None or st.session_state.embeddings_df.empty:
        # Display error message
        st.error(
            "Add files in " + st.session_state.product_category + " file storage",
            icon="🚨",
        )
    # Check if search term is empty
    elif search_term == "":
        # Display error message
        st.error(
            "Write the query to get the answer",
            icon="🚨",
        )
    else:
        # Clear previous results
        st.empty()

        # Update session state with search term
        st.session_state.rag_search_term = search_term

        # Generate RAG answers and references
        with st.spinner("Loading answer..."):
            st.session_state.rag_search_term = search_term
            (
                st.session_state.rag_answer,
                st.session_state.rag_answer_references,
            ) = insights.generate_insights_search_result(
                st.session_state.rag_search_term
            )

            # Get new suggestions
            with st.spinner("Getting new Suggestions"):
                insights.get_suggestions("temp_suggestions")

# Check if RAG answer and references are available
if (
    st.session_state.rag_answer is not None
    and st.session_state.rag_answer_references is not None
):
    # Display RAG answer
    st.write(st.session_state.rag_answer)
    st.write()

    # Display RAG answer references
    st.write("**REFERENCES**")
    st.write(st.session_state.rag_answer_references)

    # Reset RAG answers generation flag
    st.session_state.rag_answers_gen = False
    st.session_state.suggestion_first_time = 0

# Check if temporary suggestions are available
if st.session_state.temp_suggestions is not None:
    # Display divider
    st.divider()

    # Display follow up questions
    st.write("**Follow up questions**")

    # Display follow up question buttons
    for suggestion in st.session_state.temp_suggestions:
        if st.button(
            suggestion,
            key=f"{suggestion} {st.session_state.rag_search_term}",
        ):
            # Update session state with selected suggestion
            st.session_state.insights_placeholder = suggestion
            # Set flag to generate RAG answers
            st.session_state.rag_answers_gen = True
            # Rerun the app
            st.rerun()
