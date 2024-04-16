"""
This module provides the 'create_email_pdf' function,
responsible for generating a PDF containing email content and an image.

* PDF Structure:
    * Includes the email's subject as a heading.
    * Incorporates the email body text.
    * Embeds a specified image.
* Formatting:  Applies layout and styling to the PDF content.
"""

import logging
import os

from app.pages_utils.utils_pdf_generation import add_formatted_page, check_add_page
from app.pages_utils.utils_pdf_template import PDFRounded as FPDF
import streamlit as st

logging.basicConfig(
    format="%(levelname)s:%(message)s", level=logging.DEBUG
)


def create_email_pdf(title, email_text, filename, image_name):
    """Creates a PDF document from an email.

    The PDF document contains the email subject, body, and an image.
    The title of the PDF document is set to the title of the email.

    Args:
        title: The title of the email.
        email_text: The body of the email.
        filename: The name of the PDF file to be created.
        image_name: The name of the image file to be included in the PDF document.
    """
    pdf = FPDF()
    parts = email_text.split("\n", 1)
    subject = parts[0]
    text = parts[1]
    add_formatted_page(pdf)

    pdf.set_xy(15, 15)
    pdf.set_text_color(106, 144, 226)
    pdf.set_font("Arial", "B", 11)
    pdf.multi_cell(
        180,
        5,
        f"{title} {st.session_state.product_category}",
        0,
        align="C",
    )

    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Arial", "B", 11)
    pdf.set_xy(17, 25)
    pdf.multi_cell(180, 5, subject, 0, align="C")
    print(os.path)
    pdf.image(f"./{image_name}", x=60, y=40, w=90, h=70)

    pages = check_add_page(pdf, text)
    pdf.set_font("Arial", "", 11)
    for i, page in enumerate(pages):
        # Check if an empty page is encountered.
        if page.strip() == "":
            continue

        # First page
        if i == 0:
            pdf.set_xy(17, 120)
            pdf.multi_cell(170, 5, page)

        # Remaining pages after the first page
        else:
            # Add new page.
            add_formatted_page(pdf)
            pdf.set_font("Arial", "", 11)

            pdf.set_xy(17, 15)
            pdf.multi_cell(170, 5, page)

    pdf.output(f"{filename}.pdf", "F")
