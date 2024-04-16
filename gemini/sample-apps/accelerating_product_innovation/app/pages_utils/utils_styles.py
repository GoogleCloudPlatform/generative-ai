"""
Defines common styles to be used within the application
"""

import base64
import streamlit as st


STYLE_SIDEBAR = """
    <style>
        [data-testid="stSidebarNav"] {{
            background-image: url({logo});
            background-repeat: no-repeat;
            background-position: 50% 5%;
            margin-top: 10%;
            background-size: 80% ;
        }}

        [data-testid="stDecoration"] {{
            background-image: linear-gradient(90deg, rgb(51 103 214), rgb(93 135 222));
        }}

        section[data-testid="stSidebar"] {{
            border-top-right-radius: 15px;    /* Rounded top right corner */
            border-bottom-right-radius: 15px; /* Rounded bottom right corner */
        }}

        .rounded-button {{
            font-family: "Source Sans Pro", sans-serif;
            display: inline-block; /* Allows for padding and other block properties on the <a> element */
            border: 1px solid #d6d6d9ff;
            background-color: transparent; /* Transparent background */
            padding: 6px 13px; /* Spacing inside the button */
            border-radius: 7px; /* Rounded corners */
            font-size: 1rem;
            cursor: pointer; /* Hand cursor on hover */
            transition: background-color 0.3s; /* Smooth transition for hover effect */
            text-decoration: none; /* Removes the default underline from the hyperlink */
            color: #313340ff !important; /* Sets the text color to black */
        }}

        .rounded-button:hover {{
            text-decoration: none;
            color: #3367d6ff !important; /* Sets the text color to black */
            border-color: #3367d6ff !important;
        }}

        [data-testid="stToolbar"] {{
            display: none;
        }}

        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
    </style>
"""


def sidebar_apply_style(style: str, image_path: str):
    """
    Adds logo to sidebar
    """

    with open(image_path, "rb") as fp:
        contents = fp.read()
        menu_image = base64.b64encode(contents).decode("utf-8")
        menu_image = "data:image/png;base64," + menu_image

    st.markdown(
        style.format(
            logo=menu_image,
            icon_click=menu_image,
        ),
        unsafe_allow_html=True,
    )
