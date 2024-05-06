"""
Utility module for image generation and editing with Imagen
"""

# pylint: disable=E0401

import io

from PIL import Image
import streamlit as st
from streamlit_drawable_canvas import st_canvas


def edit_image_canvas(result_image_key: str, background_image: bytes):
    """This function allows users to edit an image using a
       Streamlit canvas component.
       The user can select a painting tool and stroke width,
       and then draw on the canvas.
       The edited image is then stored in the Streamlit
       session state and can be displayed.

    Args:
        result_image_key (str):
            The key to store the edited image in the Streamlit session state.
        background_image (bytes):
            The background image to be edited.
    """
    # Specify canvas parameters in application
    drawing_dict = {
        "⬜ Rectangle": "rect",
        "🖌️ Brush": "freedraw",
        "⚪ Circle": "circle",
        "📏 Move/Scale/Rotate": "transform",
    }

    drawing_mode = st.selectbox(
        (
            "[Optional] Draw a mask where you want to edit the image "
            "using one of the provided drawing tools"
        ),
        drawing_dict.keys(),
        key=f"{result_image_key}_canvas_selectbox",
    )

    stroke_width = st.slider(
        "Stroke width: ", 10, 50, 20, key=f"{result_image_key}_canvas_slider"
    )

    background_image_pil = Image.open(io.BytesIO(background_image))
    height = int(background_image_pil.size[1] / (background_image_pil.size[0] / 704))
    background = Image.new("RGB", background_image_pil.size)

    # Create a canvas component
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 1)",
        stroke_width=stroke_width,
        stroke_color="rgba(255, 255, 255, 1)",
        background_color="#000",
        background_image=background_image_pil,  # type: ignore
        update_streamlit=True,
        height=height,
        width=704,
        drawing_mode=drawing_dict[drawing_mode] if drawing_mode is not None else "rect",
        point_display_radius=0,
        key=f"{result_image_key}_canvas",
    )

    # Do something interesting with the image data and paths
    if canvas_result.image_data is not None and canvas_result.image_data.any():
        foreground = Image.fromarray(canvas_result.image_data)
        foreground_merge = foreground.resize(background.size)
        image_merge = background.copy()
        image_merge.paste(foreground_merge, (0, 0), foreground_merge)
        with io.BytesIO() as buffer_out:
            image_merge.save(buffer_out, format="PNG")
            bytes_data = buffer_out.getvalue()
        st.session_state[result_image_key] = bytes_data
        # st.image(image_merge.resize(foreground.size))
