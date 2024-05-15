"""
Utility module to:
 - Resize image bytes
 - Generate an image with Imagen
 - Edit an image with Imagen
 - Render the image generation and editing UI
"""

# pylint: disable=E0401
# pylint: disable=R0913
# pylint: disable=R0914
# pylint: disable=R0912
# pylint: disable=W0212

from typing import List

from config import config
import streamlit as st
import utils_edit_image
import vertexai
from vertexai.preview.vision_models import Image, ImageGenerationModel

# Set project parameters
PROJECT_ID = config["PROJECT_ID"]
LOCATION = config["LOCATION"]

SAMPLE_COUNT = [4, 2, 1]
SAMPLE_IMAGE_SIZE = [256, 64, 512, 1024]
ASPECT_RATIO = ["1:1", "5:4", "3:2", "7:4", "4:3", "16:9", "9:16"]

vertexai.init(project=PROJECT_ID, location=LOCATION)

model = ImageGenerationModel.from_pretrained("imagegeneration@002")


def image_generation(
    prompt: str,
    sample_count: int,
    state_key: str,
) -> List:
    """Generates an image from a prompt.

    Args:
        prompt:
            The prompt to use to generate the image.
        sample_count:
            The number of images to generate.
        state_key:
            The key to use to store the generated images in the session state.

    Returns:
        None.
    """
    imgs = model.generate_images(
        prompt=prompt,
        number_of_images=sample_count,
        language="en",
    )
    st.session_state[state_key] = imgs.images
    return imgs.images


def edit_image_generation(
    prompt: str,
    sample_count: int,
    bytes_data: bytes,
    state_key: str,
    mask_bytes_data: bytes = b"",
):
    """Generates an edited image from a prompt and a base image.

    Args:
        prompt:
            A string that describes the desired edit to the image.
        sample_count:
            The number of edited images to generate.
        bytes_data:
            The image data in bytes.
        state_key:
            The key to store the generated images in the session state.
        mask_bytes_data:
            The mask data in bytes.

    Returns:
        None.
    """
    input_dict = {
        "prompt": prompt,
        "image": Image(image_bytes=bytes_data),
    }
    input_dict["mask"] = None
    if mask_bytes_data:
        input_dict["mask"] = Image(image_bytes=mask_bytes_data)

    st.session_state[state_key] = model.edit_image(
        prompt=input_dict["prompt"],
        base_image=input_dict["image"],
        # Optional parameters
        number_of_images=sample_count,
        language="en",
        mask=input_dict["mask"],
    ).images


def render_one_image(
    images_key: str,
    image_position: int,
    edit_button: bool = False,
    image_to_edit_key: str = "",
    download_button: bool = True,
):
    """
    Renders one image from a list of images.

    Args:
        images_key:
            The key in the session state that stores the list of images.
        image_position:
            The index of the image to render.
        edit_button:
            Whether to show a button that allows the user to edit the image.
        image_to_edit_key:
            The key in the session state to store the edited image.
        download_button:
            Whether to show a button that allows the user to download the image.

    Returns:
        None.
    """
    image = st.session_state[images_key][image_position]._image_bytes
    st.image(image)

    col1, col2, _ = st.columns(3)

    with col1:
        if download_button:
            st.download_button(
                # label='Download',
                label=":arrow_down:",
                key=f"_btn_download_{images_key}_{image_position}",
                data=image,
                file_name="image.png",
            )

    with col2:
        if edit_button and image_to_edit_key:
            if st.button(":pencil2:", key=f"_btn_edit_{images_key}_{image_position}"):
                st.session_state[image_to_edit_key] = image


def generate_image_columns(
    images_key: str,
    edit_button: bool = True,
    image_to_edit_key: str = "",
    download_button: bool = True,
):
    """Generates a grid of image columns.

    Args:
        images_key (str):
            The key in the session state that stores the images.
        edit_button (bool, optional):
            Whether to show a button to edit the image. Defaults to False.
        image_to_edit_key (str, optional):
            The key in the session state that stores the image to edit. Defaults to an empty string.
        download_button (bool, optional):
            Whether to show a button to download the image. Defaults to True.

    Returns:
        None.
    """
    image_count = len(st.session_state[images_key])
    counter = 0

    st.session_state["edit_clicked"] = False
    while image_count > 0:
        cols = st.columns([25, 25, 25, 25])
        for i, col in enumerate(cols):
            with col:
                render_one_image(
                    images_key,
                    i + counter,
                    edit_button,
                    image_to_edit_key,
                    download_button,
                )
        counter += 4
        image_count -= 4


def render_image_generation_ui(
    image_text_prompt_key: str,
    generated_images_key: str,
    pre_populated_prompts: List[str],
    edit_button: bool = False,
    title: str = "Generate Images",
    image_to_edit_key: str = "",
    download_button: bool = True,
    auto_submit_first_pre_populated: bool = False,
):
    """Renders a user interface for generating images.

    Args:
        image_text_prompt_key:
            The key used to store the user's text prompt in the session state.
        generated_images_key:
            The key used to store the generated images in the session state.
        pre_populated_prompts:
            A list of pre-populated prompts.
        edit_button:
            Whether to show a button to edit the selected image.
        title:
            The title of the user interface.
        image_to_edit_key:
            The key used to store the image to edit in the session state.
        download_button:
            Whether to show a button to download the generated images.
        auto_submit_first_pre_populated:
            Whether to automatically submit the form with the first pre-populated prompt.

    Returns:
        None.
    """

    def submitted():
        st.session_state[image_text_prompt_key] = st.session_state[
            f"{image_text_prompt_key}_text_area"
        ]

    if image_text_prompt_key in st.session_state:
        st.session_state[f"{image_text_prompt_key}_text_area"] = st.session_state[
            image_text_prompt_key
        ]

    with st.form("image_form"):
        st.write(f"**{title}**")

        select_prompt = st.selectbox(
            "Select one of the pre populated prompts", pre_populated_prompts
        )

        expanded = (
            f"{image_text_prompt_key}_text_area" in st.session_state
            and st.session_state[f"{image_text_prompt_key}_text_area"] != ""
        )

        with st.expander("[Optional] Write a custom prompt", expanded=expanded):
            st.write(
                """Provide a custom prompt to generate images.
                If you provide a custom prompt, the selected option from
                the dropdown menu will not be considered."""
            )
            image_custom_prompt = st.text_area(
                "Generate a custom prompt using natural language",
                key=f"{image_text_prompt_key}_text_area",
            )

        st.write("**Model parameters**")
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            sample_count = st.selectbox("Number of samples", SAMPLE_COUNT)
        with col2:
            _ = st.selectbox("Sample Image Size", SAMPLE_IMAGE_SIZE)
        with col3:
            _ = st.selectbox("Aspect Ratio", ASPECT_RATIO, disabled=True)

        # Every form must have a submit button.
        submit_prompt = st.form_submit_button("Submit", on_click=submitted)

    if submit_prompt:
        if image_custom_prompt != "":
            st.session_state[image_text_prompt_key] = image_custom_prompt
            question = image_custom_prompt
        else:
            question = select_prompt

        with st.spinner("Generating images ..."):
            image_generation(
                question or "",
                sample_count or 1,
                generated_images_key,
            )

    if auto_submit_first_pre_populated:
        if generated_images_key not in st.session_state:
            with st.spinner("Generating images ..."):
                image_generation(
                    pre_populated_prompts[0],
                    SAMPLE_COUNT[0],
                    generated_images_key,
                )

    if generated_images_key in st.session_state:
        generate_image_columns(
            generated_images_key,
            edit_button,
            image_to_edit_key,
            download_button,
        )


def render_image_edit_prompt(
    edit_image_prompt_key: str,
    edited_images_key: str,
    upload_file: bool = True,
    image_to_edit_key: str = "",
    mask_image: bool = False,
    mask_image_key: str = "",
    download_button: bool = True,
    file_uploader_key: str = "",
):
    """
    Renders a prompt for editing an image.

    Args:
        edit_image_prompt_key:
            The key to store the edit image prompt in the session state.
        edited_images_key:
            The key to store the edited images in the session state.
        upload_file:
            Whether to allow users to upload an image to edit.
        image_to_edit_key:
            The key to store the image to edit in the session state.
        mask_image:
            Whether to allow users to mask the image to edit.
        mask_image_key:
            The key to store the mask image in the session state.
        select_button:
            Whether to show a button to select an image to edit.
        selected_image_key:
            The key to store the selected image in the session state.
        download_button:
            Whether to show a button to download the edited images.
        file_uploader_key:
            The key to store the file uploader in the session state.

    Returns:
        None.
    """

    def submitted():
        st.session_state[edit_image_prompt_key] = st.session_state[
            f"{edit_image_prompt_key}_text_area"
        ]

    if edit_image_prompt_key in st.session_state:
        st.session_state[f"{edit_image_prompt_key}_text_area"] = st.session_state[
            edit_image_prompt_key
        ]

    if upload_file:
        with st.form(f"{file_uploader_key}_form", clear_on_submit=True):
            uploaded_file = st.file_uploader(
                "Upload your image here. It MUST be in PNG or JPEG format.",
                type=["png", "jpg"],
                key=file_uploader_key,
            )
            submit_button_uploader = st.form_submit_button("Upload Image")
        if submit_button_uploader:
            if uploaded_file is not None:
                st.session_state[image_to_edit_key] = uploaded_file.getvalue()
                if mask_image and mask_image_key in st.session_state:
                    del st.session_state[mask_image_key]

    if image_to_edit_key in st.session_state:
        if image_to_edit_key in st.session_state and mask_image:
            with st.expander(
                "**[Optional] Paint where to edit in the image**", expanded=True
            ):
                utils_edit_image.edit_image_canvas(
                    mask_image_key, st.session_state[image_to_edit_key]
                )
        else:
            st.image(st.session_state[image_to_edit_key])

        with st.form(f"{edited_images_key}_edit_image"):
            st.write("**Generate edited images**")

            edit_image_prompt = st.text_area(
                "Generate a prompt using natural language to edit the image",
                key=f"{edit_image_prompt_key}_text_area",
            )

            st.write("**Model parameters**")
            col1, _, _ = st.columns([1, 1, 1])

            with col1:
                sample_count = st.selectbox("Number of samples", SAMPLE_COUNT)

            submit_button = st.form_submit_button("Edit Image", on_click=submitted)

        if submit_button:
            bytes_data = st.session_state[image_to_edit_key]

            if bytes_data:
                if not edit_image_prompt:
                    st.error("Provide a prompt for editing the image")
                else:
                    st.session_state[edit_image_prompt_key] = edit_image_prompt
                    with st.spinner("Generating edited images ..."):
                        edit_image_generation(
                            st.session_state[edit_image_prompt_key],
                            sample_count or 1,
                            bytes_data,
                            edited_images_key,
                            (
                                st.session_state.get(mask_image_key, b"")
                                if mask_image and mask_image_key
                                else b""
                            ),
                        )
            else:
                st.error("No image found to edit")

    if edited_images_key in st.session_state:
        generate_image_columns(
            edited_images_key,
            download_button=download_button,
        )


def render_image_generation_and_edition_ui(
    image_text_prompt_key: str,
    generated_images_key: str,
    edit_image_prompt_key: str,
    pre_populated_prompts: List[str],
    edit_button: bool = False,
    title: str = "Generate Images",
    image_to_edit_key: str = "",
    edit_with_mask: bool = False,
    mask_image_key: str = "",
    edited_images_key: str = "",
    download_button: bool = False,
    auto_submit_first_pre_populated=False,
):
    """Renders a user interface for generating and editing images.

    This function renders a user interface that allows users to:

    - Generate images from text prompts.
    - Edit existing images using text prompts.
    - Download generated and edited images.

    Args:
        image_text_prompt_key:
            The key used to store the user's text prompt for generating images in the session state.
        generated_images_key:
            The key used to store the generated images in the session state.
        edit_image_prompt_key:
            The key used to store the user's text prompt for editing images in the session state.
        pre_populated_prompts:
            A list of pre-populated prompts for generating images.
        select_button:
            Whether to show a button to select an image to edit.
        selected_image_key:
            The key used to store the selected image in the session state.
        edit_button:
            Whether to show a button to edit the selected image.
        title:
            The title of the user interface.
        image_to_edit_key:
            The key used to store the image to edit in the session state.
        edit_with_mask:
            Whether to allow users to mask the image to edit.
        mask_image_key:
            The key used to store the mask image in the session state.
        edited_images_key:
            The key used to store the edited images in the session state.
        download_button:
            Whether to show a button to download the generated and edited images.
        auto_submit_first_pre_populated:
            Whether to automatically submit the form with the first pre-populated prompt.

    Returns:
        None.
    """
    render_image_generation_ui(
        image_text_prompt_key,
        generated_images_key,
        pre_populated_prompts,
        edit_button,
        title,
        image_to_edit_key,
        download_button,
        auto_submit_first_pre_populated,
    )

    if image_to_edit_key in st.session_state:
        render_image_edit_prompt(
            edit_image_prompt_key,
            edited_images_key,
            False,
            image_to_edit_key,
            edit_with_mask,
            mask_image_key,
            download_button,
        )
