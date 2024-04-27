import base64

import streamlit as st
from streamlit.components.v1 import html


def nav_page(page_name, timeout_secs=3):
    """Navigates to a page in the Streamlit app.

    Args:
        page_name (str): The name of the page to navigate to.
        timeout_secs (int, optional): The number of seconds to wait for the page to load. Defaults to 3.

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


def render_svg(svg_image_path):
    """Renders an svg image
    Args:
        svg_image_path (str): The SVG string path to render.

    """
    """Renders the svg string at given path."""

    st.markdown(f"""
    <div style="text-align: center;">
        <img src="{svg_image_path}" alt="Logo">
    </div>
    """,
                unsafe_allow_html=True
                )


def build_markup_for_logo(
    png_file_path,
    background_position="50% 10%",
    margin_top="5%",
    image_width="80%",
    image_height="",
):
    """Builds the HTML markup for a logo.

    Args:
        png_file_path (str): The source path to the PNG file of the logo.
        background_position (str, optional): The background position of the logo. Defaults to "50% 10%".
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


def add_logo(png_file_path):
    """Adds a logo to the sidebar.

    Args:
        png_file_path (str): The source path to the PNG file of the logo.

    """
    logo_markup = build_markup_for_logo(png_file_path)
    st.markdown(
        logo_markup,
        unsafe_allow_html=True,
    )
