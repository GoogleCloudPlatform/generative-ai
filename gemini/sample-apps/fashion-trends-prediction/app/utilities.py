import base64
import urllib.request

import streamlit as st
from PIL import Image as ImagePIL
from rembg import remove
from streamlit.components.v1 import html


def stImg(file):
    """Converts an image file to a base64 encoded string.

    Args:
        file (str): The path to the image file.

    Returns:
        str: The base64 encoded string of the image.

    """
    with open(file, "rb") as fp:
        contents = fp.read()
        img = base64.b64encode(contents).decode("utf-8")
        img = "data:image/png;base64," + img

    return img


def unique(sentence):
    """Removes duplicate words from a sentence.

    Args:
        sentence (str): The sentence to remove duplicate words from.

    Returns:
        str: The sentence with duplicate words removed.

    """
    return " ".join(dict.fromkeys(sentence.split()))


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


def get_base64_of_bin_file(png_file):
    """Converts a binary file to a base64 encoded string.

    Args:
        png_file (str): The path to the binary file.

    Returns:
        str: The base64 encoded string of the binary file.

    """
    with open(png_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


def render_svg(svg):
    """Renders an SVG string.

    Args:
        svg (str): The SVG string to render.

    """
    """Renders the given svg string."""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    html = r'<img src="data:image/svg+xml;base64,%s"/>' % b64
    st.write(html, unsafe_allow_html=True)


def build_markup_for_logo(
    png_file,
    background_position="50% 10%",
    margin_top="5%",
    image_width="80%",
    image_height="",
):
    """Builds the HTML markup for a logo.

    Args:
        png_file (str): The path to the PNG file of the logo.
        background_position (str, optional): The background position of the logo. Defaults to "50% 10%".
        margin_top (str, optional): The margin top of the logo. Defaults to "5%".
        image_width (str, optional): The width of the logo. Defaults to "80%".
        image_height (str, optional): The height of the logo. Defaults to "".

    Returns:
        str: The HTML markup for the logo.

    """
    binary_string = get_base64_of_bin_file(png_file)
    return """
            <style>
                [data-testid="stSidebarNav"] {
                    background-image: url("data:image/png;base64,%s");
                    background-repeat: no-repeat;
                    background-position: %s;
                    margin-top: %s;
                    background-size: %s %s;
                }
            </style>
            """ % (
        binary_string,
        background_position,
        margin_top,
        image_width,
        image_height,
    )


def add_logo(png_file):
    """Adds a logo to the sidebar.

    Args:
        png_file (str): The path to the PNG file of the logo.

    """
    logo_markup = build_markup_for_logo(png_file)
    st.markdown(
        logo_markup,
        unsafe_allow_html=True,
    )
