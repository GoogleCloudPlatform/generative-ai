"""
This module manages the 'Insights' page of the Streamlit application.
It provides the following functionality:

* Project Management: Displays currently selected project.
* Data Handling:
    * Checks for uploaded files in the specified project category.
    * Loads File Data (if uploaded files exist).
* Question & Answer (QA):
    * Offers suggested questions for insights (requires uploaded data)
      through Retreival Augmented Generation.
    * Enables users to input their own questions.
    * Generates answers to questions based on uploaded data, including references.
* Follow-up Questions: Suggests follow-up questions based on previous queries.
"""

import base64

import app.pages_utils.utils as utils
from app.pages_utils.utils_config import PAGES_CFG
import app.pages_utils.utils_insights as utils_insights
import app.pages_utils.utils_styles as utils_styles
import streamlit as st

# Initialize session state if not already
if "initialize_session_state" not in st.session_state:
    st.session_state.initialize_session_state = False

if st.session_state.initialize_session_state is False:
    utils.initialize_all_session_state()
    st.session_state.initialize_session_state = True

# Initialize temporary suggestions if not already initialized
if "temp_suggestions" not in st.session_state:
    st.session_state.temp_suggestions = None

# Get page configuration from config file
page_cfg = PAGES_CFG["2_Marketing_Insights"]

# Set page configuration
st.set_page_config(
    page_title=page_cfg["page_title"],
    page_icon=page_cfg["page_icon"],
    layout="wide",
)

# Apply custom styling to sidebar
utils_styles.sidebar_apply_style(
    style=utils_styles.STYLE_SIDEBAR,
    image_path=page_cfg["sidebar_image_path"],
)


# Cache the function to get insights images
@st.cache_data
def get_insights_img():
    """
    Loads header image for insights page.
    """
    file_name_1 = page_cfg["prod_insights_1"]
    file_name_2 = page_cfg["prod_insights_2"]

    with open(file_name_1, "rb") as fp:
        contents = fp.read()
        main_image_1 = base64.b64encode(contents).decode("utf-8")
        main_image_1 = "data:image/png;base64," + main_image_1

    with open(file_name_2, "rb") as fp:
        contents = fp.read()
        main_image_2 = base64.b64encode(contents).decode("utf-8")
        main_image_2 = "data:image/png;base64," + main_image_2

    return main_image_1, main_image_2


# Get insights images
prod_insights_1, prod_insights_2 = get_insights_img()

# Display insights images
st.image(prod_insights_1)
st.divider()
st.image(prod_insights_2)

# Display projects
utils.display_projects()

# Check if data frame is empty
if st.session_state.dff is None or st.session_state.dff.empty:
    with st.spinner("Fetching Uploaded Files..."):
        dff = utils_insights.check_if_file_uploaded()
        st.session_state.dff = dff


# Function to display suggestion box
def display_suggestion_box(key, suggestion_num):
    """
    Styles and displays the suggestion for insight generation.
    Args:
        key: Unique key for suggestion.
        suggestion_num: Current suggestion number.
    """
    # Apply custom styling to suggestion box
    st.markdown(
        "<style>.element-container:has(#button-after) + div button {{min-height: 100px; max-width:500px;min-width:500px; border-radius: 25px;}}</style>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<span id="button-after"></span>',
        unsafe_allow_html=True,
    )

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
if st.session_state.dff.empty:
    # Display error message
    st.error(
        "Add files in "
        + st.session_state.product_category
        + " file storage to get suggested questions",
        icon="🚨",
    )
else:
    # Loop until suggestions are loaded or try limit is reached
    TRY_VAR = 0
    while (
        st.session_state.suggestion_first_time
        and st.session_state.insights_suggestion is None
        and TRY_VAR < 3
    ):
        TRY_VAR += 1
        with st.spinner("Loading suggestion..."):
            utils_insights.get_suggestions("insights_suggestion")
            # Check if number of suggestions is less than 4
            if (
                st.session_state.insights_suggestion is not None
                and len(st.session_state.insights_suggestion) < 4
            ):
                utils_insights.get_suggestions("insights_suggestion")

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

# Create columns for query and search button
query_column = st.columns([4, 1])

# Get search term from text area
with query_column[0]:
    search_term = st.text_area(
        "",
        key="2",
        value=st.session_state.insights_placeholder,
        placeholder="Select a suggestion or type your question here",
    )

# Create empty space in second column
with query_column[1]:
    st.write("")
    st.write("")
    st.write("")
    st.write("")

    # Display search button
    if st.button("Search", type="primary"):
        # Set flag to generate RAG answers
        st.session_state.rag_answers_gen = True

# Check if RAG answers should be generated
if st.session_state.rag_answers_gen is True:
    # Check if data frame is empty
    if st.session_state.dff.empty:
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
            ) = utils_insights.generate_insights_search_result(
                st.session_state.rag_search_term
            )

            # Get new suggestions
            with st.spinner("Getting new Suggestions"):
                utils_insights.get_suggestions("temp_suggestions")

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
