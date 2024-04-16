"""
This module provides functions for adding and formatting content within PDF documents.

* add_formatted_page(pdf):
    * Adds a standard-format page with a light gray background and a centered white rectangle.

* check_add_page(pdf, text):
    * Handles potential text overflow onto subsequent pages. 
"""


def add_formatted_page(pdf):
    """Adds a formatted page to the PDF document.

    The page is filled with a light gray color and has a white rectangle in the center.
    The font is set to Arial, bold, size 18, and the fill color is set to white.

    Args:
        pdf: The PDF document to which the page is added.
    """
    pdf.set_fill_color(225, 230, 237)
    pdf.add_page()
    pdf.rect(0, 0, 210, 297, "F")
    pdf.set_font("Arial", "B", 18)
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(10, 10, 190, 277, "F")


def check_add_page(pdf, text):
    """Checks if the text overflows onto a new page and adds a new page if necessary.

    The text is split into lines based on the available page width.
    If the text overflows onto a new page, a new page is added and the text
    is continued on the new page.

    Args:
        pdf: The PDF document to which the text is added.
        text: The text to be added to the PDF document.
        lim: The maximum number of characters that can fit on a single page.

    Returns:
        A list of pages, where each page is a string containing the text that fits on that page.
    """

    pages = []  # Store the text content for each page
    page_content = ""  # Text for the current page being built

    pdf.set_font("Arial", "", 11)

    # Split the text into lines based on the available page width
    lines = []
    y = pdf.y

    for line in text.split("\n"):
        words = line.split(" ")
        current_line = ""  # Represents a single line within the page

        for word in words:
            # Check if adding the word would exceed the line limit
            if len(current_line + word) > pdf.w - pdf.l_margin - pdf.r_margin:
                lines.append(current_line)
                page_content += current_line + "\n"
                current_line = ""  # Reset for the next line
            current_line += word + " "

        if current_line:
            lines.append(current_line)
            # Check if adding the line would overflow the page
            if y + 10 > pdf.h - (80 if len(pages) == 0 else 0):
                pages.append(page_content)  # Add the new page to the PDF
                page_content = current_line + "\n"  # Start a new page
                y = 10
            else:
                # Add the completed line to the current page
                page_content += current_line + "\n"
            y += 10

    # Add any remaining text to the final page
    pages.append(page_content)
    return pages
