"""
Common utilities for the project. This includes:
    * session state initialization.
    * project selection.
"""

import app.pages_utils.utils_project as utils_project
import streamlit as st
import app.pages_utils.utils_styles as utils_styles


def display_projects():
    """Displays the list of projects and allows the user to select one.

    Args:
        None

    Returns:
        None
    """
    st.session_state.product_category = st.selectbox(
        "Select a project", st.session_state.product_categories
    )
    st.session_state.product_categories.remove(st.session_state.product_category)
    st.session_state.product_categories.insert(0, st.session_state.product_category)
    if st.session_state.previous_product_category != st.session_state.product_category:
        reinitialize_session_states()
        st.session_state.previous_product_category = st.session_state.product_category
        st.rerun()


def initialize_all_session_state():
    """Initializes all the session states used in the app.

    Args:
        None

    Returns:
        None
    """
    if "product_categories" not in st.session_state:
        st.session_state.product_categories = utils_project.get_projects_list()
    if "product_category" not in st.session_state:
        st.session_state.product_category = st.session_state.product_categories[0]
    if "input_csv_file_to_pd" not in st.session_state:
        st.session_state.input_csv_file_to_pd = None
    if "st.session_state.current_filename" not in st.session_state:
        st.session_state.current_filename = None
    if "pd_header" not in st.session_state:
        st.session_state.pd_header = None
    if "new_product_category_added" not in st.session_state:
        st.session_state.new_product_category_added = None
    if "previous_product_category" not in st.session_state:
        st.session_state.previous_product_category = None
    if "edit_content_prompt_submit" not in st.session_state:
        st.session_state.edit_content_prompt_submit = None
    if "st.session_state.text_edit_prompt" not in st.session_state:
        st.session_state.text_edit_prompt = None
    if "st.session_state.update_text_btn" not in st.session_state:
        st.session_state.update_text_btn = None
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = None
    if "rag_search_term" not in st.session_state:
        st.session_state.rag_search_term = None
    if "rag_answers_gen" not in st.session_state:
        st.session_state.rag_answers_gen = False
    if "rag_answer" not in st.session_state:
        st.session_state.rag_answer = None
    if "rag_answer_references" not in st.session_state:
        st.session_state.rag_answer_references = None
    if "insights_suggestion" not in st.session_state:
        st.session_state.insights_suggestion = None
    if "insights_placeholder" not in st.session_state:
        st.session_state.insights_placeholder = ""
    if "suggestion_clicked" not in st.session_state:
        st.session_state.suggestion_clicked = ""
    if "store_suggestion" not in st.session_state:
        st.session_state.store_suggestion = None
    if "suggestion_first_time" not in st.session_state:
        st.session_state.suggestion_first_time = 1
    if "insights_suggestion_toggle" not in st.session_state:
        st.session_state.insights_suggestion_toggle = 1
    if "insights_answer_toggle" not in st.session_state:
        st.session_state.insights_answer_toggle = 1
    if "processed_data_list" not in st.session_state:
        st.session_state["processed_data_list"] = []
    if "query_vectors" not in st.session_state:
        st.session_state["query_vectors"] = []
    if "dff" not in st.session_state:
        st.session_state.dff = None
    if "temp_suggestions" not in st.session_state:
        st.session_state.temp_suggestions = None
    if "assorted_prod_title" not in st.session_state:
        st.session_state.assorted_prod_title = None
    if "assorted_prod_content" not in st.session_state:
        st.session_state.assorted_prod_content = []
    if "email_gen" not in st.session_state:
        st.session_state.email_gen = False
    if "create_product" not in st.session_state:
        st.session_state.create_product = False
    if "modifying" not in st.session_state:
        st.session_state.modifying = False
    if "post_gen" not in st.session_state:
        st.session_state.post_gen = False
    if "blog_gen" not in st.session_state:
        st.session_state.blog_gen = False
    if "custom_prompt" not in st.session_state:
        st.session_state.custom_prompt = ""
    if "product_name" not in st.session_state:
        st.session_state.product_name = "sunscreen"
    if "feature_suggestions" not in st.session_state:
        st.session_state.feature_suggestions = None
    if "selected_titles" not in st.session_state:
        st.session_state.selected_titles = []
        st.session_state.saved_titles = []
    if "selected_prompt" not in st.session_state:
        st.session_state.selected_prompt = None
    if "product_gen_image" not in st.session_state:
        st.session_state.product_gen_image = None
    if "features_generated" not in st.session_state:
        st.session_state.features_generated = False
    if "generated_points" not in st.session_state:
        st.session_state.generated_points = None
    if "content_generated" not in st.session_state:
        st.session_state.content_generated = False
    if "product_content" not in st.session_state:
        st.session_state.product_content = None
    if "image_to_edit" not in st.session_state:
        st.session_state.image_to_edit = -1
    if "generate_images" not in st.session_state:
        st.session_state.generate_images = False
    if "image_prompt" not in st.session_state:
        st.session_state.image_prompt = None
    if "image_file_prefix" not in st.session_state:
        st.session_state.image_file_prefix = None
    if "generate_images" not in st.session_state:
        st.session_state.generate_images = None
    if "email_image" not in st.session_state:
        st.session_state.email_image = None
    if "email_prompt" not in st.session_state:
        st.session_state.email_prompt = "High SPF"
    if "num_email_drafts" not in st.session_state:
        st.session_state.num_email_drafts = 2
    if "num_drafts" not in st.session_state:
        st.session_state.num_drafts = None
    if "email_text" not in st.session_state:
        st.session_state.email_text = None
    if "generated_image" not in st.session_state:
        st.session_state.generated_image = None
    if "mask_image" not in st.session_state:
        st.session_state.mask_image = None
    if "edit_suggestion" not in st.session_state:
        st.session_state.edit_suggestion = False
    if "suggested_images" not in st.session_state:
        st.session_state.suggested_images = None
    if "uploaded_img" not in st.session_state:
        st.session_state.uploaded_img = False
    if "image_file_prefix" not in st.session_state:
        st.session_state.image_file_prefix = "./uploaded_image"
    if "start_editing" not in st.session_state:
        st.session_state.start_editing = False
    if "generate_images" not in st.session_state:
        st.session_state.generate_images = False
    if "image_prompt" not in st.session_state:
        st.session_state.image_prompt = None
    if "text_to_edit" not in st.session_state:
        st.session_state.text_to_edit = None
    if "image_to_edit" not in st.session_state or st.session_state.image_to_edit == -1:
        st.session_state.image_to_edit = -1
        st.session_state.image_file_prefix = "./uploaded_image"
        st.session_state.uploaded_img = True
    else:
        st.session_state.start_editing = True
    if "content_edited" not in st.session_state:
        st.session_state.content_edited = None
    if "row" not in st.session_state:
        st.session_state.row = None
    if "edited_content" not in st.session_state:
        st.session_state.edited_content = None
    if "col" not in st.session_state:
        st.session_state.col = None
    if "generated_response" not in st.session_state:
        st.session_state.generated_response = None
    if "draft_elements" not in st.session_state:
        st.session_state.draft_elements = None
    if "chosen_titles" not in st.session_state:
        st.session_state.chosen_titles = []
    if "buffer" not in st.session_state:
        st.session_state.buffer = None
    if "save_edited_image" not in st.session_state:
        st.session_state.save_edited_image = None
    if "email_files" not in st.session_state:
        st.session_state.email_files = []
    if "st.session_state.image_edit_col" not in st.session_state:
        st.session_state.image_edit_col = None
    if "st.session_state.image_edit_row" not in st.session_state:
        st.session_state.image_edit_row = None
    if "st.session_state.bg_editing" not in st.session_state:
        st.session_state.bg_editing = False


def reinitialize_session_states():
    """Reinitializes all the session states used in the app.

    Args:
        None

    Returns:
        None
    """
    st.session_state.insights_suggestion = None
    st.session_state.dff = None
    st.session_state.custom_prompt = ""
    st.session_state.temp_suggestions = None
    st.session_state.feature_suggestions = None
    st.session_state.drafts_generated = False
    st.session_state.generated_response = None
    st.session_state.content_generated = False
    st.session_state.create_product = False
    st.session_state.selected_titles = []
    st.session_state.product_content = []
    st.session_state.suggestion_first_time = 1
    #######################################################
    st.session_state.input_csv_file_to_pd = None
    st.session_state.current_filename = None
    st.session_state.pd_header = None
    st.session_state.new_product_category_added = None
    st.session_state.edit_content_prompt_submit = None
    st.session_state.text_edit_prompt = None
    st.session_state.update_text_btn = None
    st.session_state.uploaded_files = None
    st.session_state.rag_search_term = None
    st.session_state.rag_answers_gen = False
    st.session_state.rag_answer = None
    st.session_state.rag_answer_references = None
    st.session_state.insights_suggestion = None
    st.session_state.insights_placeholder = ""
    st.session_state.suggestion_clicked = ""
    st.session_state.store_suggestion = None
    st.session_state.suggestion_first_time = 1
    st.session_state.insights_suggestion_toggle = 1
    st.session_state["processed_data_list"] = []
    st.session_state["query_vectors"] = []
    st.session_state.dff = None
    st.session_state.temp_suggestions = None
    st.session_state.assorted_prod_title = None
    st.session_state.assorted_prod_content = []
    st.session_state.email_gen = False
    st.session_state.create_product = False
    st.session_state.modifying = False
    st.session_state.post_gen = False
    st.session_state.blog_gen = False
    st.session_state.custom_prompt = ""
    st.session_state.product_name = "sunscreen"
    st.session_state.feature_suggestions = None
    st.session_state.selected_titles = []
    st.session_state.saved_titles = []
    st.session_state.selected_prompt = None
    st.session_state.product_gen_image = None
    st.session_state.features_generated = False
    st.session_state.generated_points = None
    st.session_state.content_generated = False
    st.session_state.product_content = None
    st.session_state.image_to_edit = -1
    st.session_state.generate_images = False
    st.session_state.image_prompt = None
    st.session_state.image_file_prefix = None
    st.session_state.generate_images = None
    st.session_state.email_image = None
    st.session_state.email_prompt = "High SPF"
    st.session_state.num_email_drafts = 2
    st.session_state.num_drafts = None
    st.session_state.email_text = None
    st.session_state.generated_image = None
    st.session_state.mask_image = None
    st.session_state.edit_suggestion = False
    st.session_state.suggested_images = None
    st.session_state.uploaded_img = False
    st.session_state.image_file_prefix = "./uploaded_image"
    st.session_state.start_editing = False
    st.session_state.generate_images = False
    st.session_state.image_prompt = None
    st.session_state.text_to_edit = None
    if "image_to_edit" not in st.session_state or st.session_state.image_to_edit == -1:
        st.session_state.image_to_edit = -1
        st.session_state.image_file_prefix = "./uploaded_image"
        st.session_state.uploaded_img = True
    else:
        st.session_state.start_editing = True
    st.session_state.content_edited = None
    st.session_state.row = None
    st.session_state.edited_content = None
    st.session_state.col = None
    st.session_state.generated_response = None
    st.session_state.draft_elements = None
    st.session_state.chosen_titles = []
    st.session_state.buffer = None
    st.session_state.save_edited_image = None
    st.session_state.email_files = []
    st.session_state.image_edit_col = None
    st.session_state.image_edit_row = None
    st.session_state.bg_editing = False


def page_setup(page_cfg):
    """
        This function initializes the page configuration and applies custom styles.

        Args:
            page_cfg (dict): A dictionary containing the configuration for the page.

        Returns:
            None
    """

    # Set the page configuration
    st.set_page_config(page_title=page_cfg["page_title"], page_icon=page_cfg["page_icon"])

     # Initialize session state for the project if it does not exist.
    if (
        "initialize_session_state" not in st.session_state
        or st.session_state.initialize_session_state is False
    ):
        initialize_all_session_state()
        st.session_state.initialize_session_state = True
    # Apply the sidebar style
    utils_styles.sidebar_apply_style(
        style=utils_styles.STYLE_SIDEBAR,
        image_path=page_cfg["sidebar_image_path"],
    )

