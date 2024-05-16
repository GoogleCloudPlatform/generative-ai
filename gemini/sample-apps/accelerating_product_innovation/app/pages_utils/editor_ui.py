"""
This module defines the 'ImageEditor' class, providing an interactive image
editing interface.
"""

import io

from PIL import Image
import streamlit as st
from streamlit_drawable_canvas import st_canvas


class ImageEditor:
    """
    Functions include:
    * Drawing Tools: Offers tools for drawing masks (rectangles,
      free drawing, circles).
    * Customization: Allows control over stroke width and drawing mode.
    * Background Editing:  Enables background modification (with masking).
    * Prompts:  Facilitates image generation based on user-provided text
      prompts.
    """

    def __init__(self):
        self.stroke_width = 20  # Default stroke width
        self.stroke_color = "black"
        self.drawing_mode = "rect"  # Default drawing mode
        self.realtime_update = True

    def load_image(self, image_file: str) -> io.BytesIO:
        """Load an image from a local file as BytesIO.
        Args:
            image_file: path to image file to be loaded.

        Returns:
            Image bytes object.
        """
        with open(image_file, "rb") as f:
            image_data = f.read()
        return io.BytesIO(image_data)

    def display_ui(self):
        """Renders the main UI components of the image editor."""
        # - Load the image for editing
        image_bytes = self.load_image(
            f"""{st.session_state.image_file_prefix}{st.session_state.image_to_edit + 1}.png"""
        )
        bg_image = Image.open(image_bytes)

        st.markdown("<h1>Edit Image</h1>", unsafe_allow_html=True)

        # Stroke Width Control
        # - Add a slider to control drawing/mask stroke width
        self.stroke_width = st.slider(
            "Stroke width: ",
            10,
            50,
            self.stroke_width,
            key="canvas_slider",
        )

        # Image Prompt Section
        with st.form("Image prompt"):
            # - Provide a description of the form's purpose
            st.write("Input a query to generate the product.")
            img_prompt = st.text_input("Enter your custom query", "")
            edit_img_btn = st.form_submit_button("Submit prompt", type="primary")

            # - Handle form submission
            if edit_img_btn:
                # -- Update session state to trigger image generation
                st.session_state.generate_images = True
                st.session_state.image_prompt = img_prompt

        # Mask Drawing Setup
        drawing_dict = {  # - Dictionary mapping descriptive names to drawing modes.
            "⬜ Rectangle": "rect",
            "🖌️ Brush": "freedraw",
            "⚪ Circle": "circle",
            "📏 Move/Scale/Rotate": "transform",
        }
        self.drawing_mode = st.selectbox(
            "[Optional] Draw a mask where you want to edit the image",
            drawing_dict.keys(),
            key="canvas_select_box",
        )

        # Canvas Setup
        height = (
            int(bg_image.size[1] / (bg_image.size[0] / 704)) // 2
        )  # - Calculate canvas height dynamically
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 1)",
            stroke_width=self.stroke_width,
            stroke_color="rgba(255, 255, 255, 1)",
            background_color="#000",
            background_image=bg_image,  # Use loaded image as background
            update_streamlit=self.realtime_update,
            height=height,
            initial_drawing=None,
            width=352,
            drawing_mode=drawing_dict[self.drawing_mode],
            point_display_radius=0,  # - Hide cursor on canvas
            key="canvas",
        )

        # Background Editing Control
        if st.checkbox("Edit Image Background"):
            st.session_state.bg_editing = True  # - Enable background editing mode
            st.write("       Please mask the area you want to preserve")
        else:
            st.session_state.bg_editing = False  # - Disable background editing

        # Return Values
        return (
            canvas_result,
            bg_image,
            image_bytes,
        )  # - Return values likely used elsewhere
