"""
This module provides functions for creating content PDFs with specific
layouts and formatting.
"""

from typing import Any

from app.pages_utils.pdf_generation import PDFRounded as pdf_generator
from app.pages_utils.pdf_generation import add_formatted_page, check_add_page
import streamlit as st


def create_pdf_layout(
    pdf: pdf_generator, content: list[str], title: str, images: list[str]
) -> None:
    """
    Creates a PDF layout with the given content, title, and images.

    Args:
        pdf: The PDF object where the layout will be created.
        content: A list of strings representing the textual content of the PDF.
        title: The title of the PDF.
        images: A list of image file names to include in the PDF.
    """

    for j, text in enumerate(content):
        add_formatted_page(pdf)

        # Set up header
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

        # Reset text color
        pdf.set_text_color(0, 0, 0)

        # Add image
        pdf.set_font("Arial", "B", 11)
        pdf.set_xy(17, 25)
        image_path = f"gen_image{images[j]}.png"
        pdf.image(image_path, x=60, y=40, w=90, h=70)

        # Add text content, handling potential page breaks
        pages = check_add_page(pdf, text)
        pdf.set_font("Arial", "", 11)

        for i, page in enumerate(pages):
            if page.strip() == "":
                continue

            if i == 0:  # First page of text
                pdf.set_xy(17, 120)
            else:  # Subsequent pages
                add_formatted_page(pdf)
                pdf.set_xy(17, 15)
                pdf.set_font("Arial", "", 11)

            pdf.multi_cell(170, 5, page)  # Output the text


def create_content_pdf(
    product_content: list[list[dict[str, Any]]], selected_titles: list[str]
) -> None:
    """Creates a PDF for each product content and selected title.

    Args:
        product_content: A list of strings representing the
        product content.
        selected_titles: A list of selected titles for each product content.
    """
    for product_index in range(len(product_content) - 1):
        pdf = pdf_generator()  # Create a PDF for the current product

        # Build content and image lists for the current product
        content = [product_content[(int)(product_index)][0]["text"].replace("**", "")]
        images = [st.session_state.num_drafts * product_index + 1]

        # Generate the PDF layout
        create_pdf_layout(pdf, content, selected_titles[product_index], images)

        # Save the PDF with an appropriate filename
        pdf.output(f"content_{product_index}.pdf")


def cut_string(string: str, num_characters: int) -> str:
    """Cuts a string to the specified number of characters.

    Args:
        string: The string to cut.
        num_characters: The number of characters to cut the string to.

    Returns:
        The cut string.
    """
    if len(string) <= num_characters:
        return string
    return string[:num_characters]


def create_email_pdf(
    title: str, email_text: str, filename: str, image_name: str
) -> None:
    """Creates a PDF document from an email.

    The PDF document contains the email subject, body, and an image.
    The title of the PDF document is set to the title of the email.

    Args:
        title: The title of the email.
        email_text: The body of the email.
        filename: The name of the PDF file to be created.
        image_name: The name of the image file to be included in the PDF
        document.
    """
    pdf = pdf_generator()

    # Extract subject and text from email text.
    parts = email_text.split("\n", 1)
    subject = parts[0]
    text = parts[1]

    # Add first page of pdf.
    add_formatted_page(pdf)

    # Set location and text style for heading.
    pdf.set_xy(15, 15)
    pdf.set_text_color(106, 144, 226)
    pdf.set_font("Arial", "B", 11)

    # Add heading to pdf object.
    pdf.multi_cell(
        180,
        5,
        f"{title} {st.session_state.product_category}",
        0,
        align="C",
    )

    # Set text location and styling for subject.
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(17, 25)

    # Add subject to pdf.
    pdf.multi_cell(180, 5, subject, 0, align="C")

    # Add image to pdf object.
    pdf.image(f"{image_name}", x=60, y=40, w=90, h=70)

    # Check if new page needs to be added, and
    # add required pages.
    # List pages stores the text content for each page.
    pages = check_add_page(pdf, text)

    # Set font style for email body.
    pdf.set_font("Arial", "", 11)

    # Add text content to each page of pdf.
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
