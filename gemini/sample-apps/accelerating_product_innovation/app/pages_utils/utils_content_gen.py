"""
This module facilitates email generation for new product concepts. It includes functions to:

*  Generate email text using a language model (Gemini).
*  Generate a corresponding product image. 
*  Combine the generated text and image into a PDF email. 
"""

import base64
import io
import logging
import os

import cv2
import numpy as np
import streamlit as st
from dotenv import load_dotenv

from app.pages_utils.utils_gen_email_pdf import create_email_pdf
from app.pages_utils.utils_get_llm_response import generate_gemini
from app.pages_utils.utils_imagen import image_generation

load_dotenv()
logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)
st.session_state.image_file_prefix = "email_image"

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")


def generate_email(prompt, title):
    """Generates an email PDF with the given prompt and title.

    Args:
        prompt (str): The prompt for the email text.
        title (str): The title of the email.
    """
    if st.session_state.email_gen:
        # Create prompt for email generation for given product idea.
        email_prompt = f"""Write an email introducing the concept for a new product, {prompt}.
        Write the benefits for different demographics, skin types, genders, etc., too. 
        The email should strictly share the concept with the innovation team. 
        The email should strictly not announce launch, only the concept. 
        Keep the email brief."""

        # Generate Email content.
        email_text = generate_gemini(email_prompt)
        st.session_state.email_text = email_text  # update state.

        # Generate corresponding image for email copy.
        image_generation(
            f"""Generate a beautiful image of a {st.session_state.product_category} 
            in an aesthetic background. Image should be suitable for advertising. 
            Content should be written on packaging in English.""",
            1,
            256,
            "1:1",
            "email_image",
        )

        # Read Byte data of the image.
        image_data = io.BytesIO(
            base64.b64decode(st.session_state.email_image[0]["bytesBase64Encoded"])
        )

        # Save image to display on pdf file.
        image_array = cv2.imdecode(np.frombuffer(image_data.read(), dtype=np.uint8), 1)
        cv2.imwrite("email_image1.png", image_array)

        # Generate pdf containing the email content and image.
        create_email_pdf(
            title,
            email_text.replace("**", ""),
            f"email_copy_0_{title}",
            "email_image1.png",
        )
        st.session_state.email_files.append(f"email_copy_0_{title}.pdf")
