"""
This module provides functions for creating content PDFs with specific 
layouts and formatting.
"""

from app.pages_utils.utils_pdf_generation import add_formatted_page, check_add_page
from app.pages_utils.utils_pdf_template import PDFRounded as FPDF
import streamlit as st


def create_pdf_layout(pdf, content, title, images):
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
            180, 5, f"{title} {st.session_state.product_category}", 0, align="C"
        )

        # Reset text color
        pdf.set_text_color(0, 0, 0)

        # Add image
        pdf.set_font("Arial", "B", 11)
        pdf.set_xy(17, 25)
        image_path = f"./gen_image{images[j]}.png"
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


def create_content_pdf(product_content, selected_titles):
    """Creates a PDF for each product content and selected title.

    Args:
        product_content: A list of lists of dictionaries representing the product content.
        selected_titles: A list of selected titles for each product content.
    """
    print("HERE....")
    for product_index in range(len(product_content) - 1):
        pdf = FPDF()  # Create a PDF for the current product
        content = []
        images = []

        # Build content and image lists for the current product
        content.append(product_content[product_index][0]["text"].replace("**", ""))
        images.append(st.session_state.num_drafts * product_index + 1)

        # Generate the PDF layout
        create_pdf_layout(pdf, content, selected_titles[product_index], images)

        # Save the PDF with an appropriate filename
        print("SAVING")

        pdf.output(f"content_{product_index}.pdf")


def cut_string(string, num_characters):
    """Cuts a string to the specified number of characters.

    Args:
        string: The string to cut.
        num_characters: The number of characters to cut the string to.

    Returns:
        The cut string.
    """
    if len(string) <= num_characters:
        return string
    else:
        return string[:num_characters]
