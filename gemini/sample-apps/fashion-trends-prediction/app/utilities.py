"""
Module for utility functions.
"""

# pylint: disable=E0401

import streamlit as st
from streamlit.components.v1 import html


def nav_page(page_name: str, timeout_secs: int = 3) -> None:
    """Navigates to a page in the Streamlit app.

    Args:
        page_name (str): The name of the page to navigate to.
        timeout_secs (int, optional): Number of seconds to wait for the page to load. Defaults to 3.

    """
    nav_script = """
        <script type="text/javascript">
            function attempt_nav_page(page_name, start_time, timeout_secs) {
                var links = window.parent.document.getElementsByTagName("a");
                for (var i = 0; i < links.length; i++) {
                    if (links[i].href.toLowerCase().endsWith("/" + page_name.toLowerCase())) {
                        links[i].click();
                        return;
                    }
                }
                var elasped = new Date() - start_time;
                if (elasped < timeout_secs * 1000) {
                    setTimeout(attempt_nav_page, 100, page_name, start_time, timeout_secs);
                } else {
                    alert("Unable to navigate to page '" + page_name + "' after " + timeout_secs + " second(s).");
                }
            }
            window.addEventListener("load", function() {
                attempt_nav_page("%s", new Date(), %d);
            });
        </script>
    """ % (
        page_name,
        timeout_secs,
    )
    html(nav_script)


def button_html_script(
    widget_label: str, btn_bg_color1: str, btn_bg_color2: str
) -> str:
    """Generates HTML script to change the color of a button.

    Args:
        widget_label (str): The label of the button.
        btn_bg_color1 (str): The background color of the button.
        btn_bg_color2 (str): The border color of the button.

    Returns:
        str: The HTML script.

    """
    return f"""
        <script>
            var elements = window.parent.document.querySelectorAll('button');
            for (var i = 0; i < elements.length; ++i) {{
                if (elements[i].innerText == '{widget_label}') {{
                    elements[i].style.color = '{btn_bg_color1}';  // Set text color
                    elements[i].style.borderColor = '{btn_bg_color2}';  // Change border color
                    elements[i].style.display = 'inline-block'; // Or 'block' if that's your original layout
                }}
            }}
        </script>
    """


def render_svg(svg_image_path: str) -> None:
    """Renders the svg string at given path.
    Args:
        svg_image_path (str): The SVG string path to render.

    """

    st.markdown(
        f"""
    <div style="text-align: center;">
        <img src="{svg_image_path}" alt="Logo">
    </div>
    """,
        unsafe_allow_html=True,
    )


def build_markup_for_logo(
    png_file_path: str,
    background_position: str = "50% 10%",
    margin_top: str = "5%",
    image_width: str = "80%",
    image_height: str = "",
) -> str:
    """Builds the HTML markup for a logo.

    Args:
        png_file_path (str): The source path to the PNG file of the logo.
        background_position (str, optional): The bg position of the logo. Defaults to "50% 10%".
        margin_top (str, optional): The margin top of the logo. Defaults to "5%".
        image_width (str, optional): The width of the logo. Defaults to "80%".
        image_height (str, optional): The height of the logo. Defaults to "".

    Returns:
        str: The HTML markup for the logo.

    """
    return """
            <style>
                [data-testid="stSidebarNav"] {
                    background-image: url("%s");
                    background-repeat: no-repeat;
                    background-position: %s;
                    margin-top: %s;
                    background-size: %s %s;
                }
            </style>
            """ % (
        png_file_path,
        background_position,
        margin_top,
        image_width,
        image_height,
    )


def add_logo(png_file_path: str) -> None:
    """Adds a logo to the sidebar.

    Args:
        png_file_path (str): The source path to the PNG file of the logo.

    """
    logo_markup = build_markup_for_logo(png_file_path)
    st.markdown(
        logo_markup,
        unsafe_allow_html=True,
    )


def details_html(key: str, values_str: str) -> str:
    """Generates HTML for displaying details in a box.

    Args:
        key (str): The key of the details.
        values_str (str): The values of the details.

    Returns:
        str: The HTML.

    """
    return f"""
            <style>
            .box-container {{
                border: 1px solid gray;
                padding: 10px;
                border-radius: 5px;
                background-color: #f5f5f5;
                margin: 15px;
            }}
            </style>
            <div class="box-container">
                <summary style='list-style: none;'>
                    <span style='color: #ff4c4b; font-size: 17px;'>{key}:<br>
                    </span>
                </summary>
                <div>
                    <span style='font-size: 16px;'>{values_str}<br>
                    </span>
                </div>
            </div>
            """


EXCEPTION_HTML = """
                    <style>
                    .box-container {
                        border: 1px solid gray;
                        padding: 120px;
                        border-radius: 5px;
                        background-color: #f5f5f5;
                    }
                    </style>
                    <div class="box-container">
                        Image generation failed due to responsible AI restrictions.
                    </div>
                """
