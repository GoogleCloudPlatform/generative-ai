"""
This module provides functions for adding and formatting content within PDF
documents.

* add_formatted_page(pdf):
    * Adds a standard-format page with a light gray background and a centered
      white rectangle.

* check_add_page(pdf, text):
    * Handles potential text overflow onto subsequent pages.

* Provides class for generating a pdf template for exporting content and
 emails.
"""

# pylint: disable=R0913

from math import sqrt

import fpdf as pdf_generator


class PDFRounded(pdf_generator.FPDF):
    """
    Initializes basic PDF template for email and content files
    """

    def rounded_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        r: float,
        style: str = "",
        corners: str = "1234",
    ):
        """
        Draws a rectangle with rounded corners.

        Args:
            x (float): The x-coordinate of the top-left corner of the
                       rectangle.
            y (float): The y-coordinate of the top-left corner of the
                       rectangle.
            w (float): The width of the rectangle.
            h (float): The height of the rectangle.
            r (float): The radius of the rounded corners.
            style (str, optional): The style of the rectangle.
            Can be 'F' for filled, 'FD' for filled and drawn,
            or 'DF' for drawn and filled. Defaults to 'S' for stroked.
            corners (str, optional): A string of characters indicating
            which corners of the rectangle should be rounded.
            Can be '1234' for all corners, '12' for the top-left and top-right
            corners,
            '34' for the bottom-left and bottom-right corners, or
            '13' for the top-left and bottom-right corners. Defaults to '1234'.
        """

        k = self.k
        hp = self.h
        if style == "F":
            op = "f"
        elif style in ("FD", "DF"):
            op = "B"
        else:
            op = "S"
        my_arc = 4 / 3 * (sqrt(2) - 1)
        self._out(f"{(x + r) * k} {(hp - y) * k} m")

        xc = x + w - r
        yc = y + r
        self._out(f"{xc * k} {(hp - y) * k} l")
        if "2" not in corners:
            self._out(f"{(x + w) * k} {(hp - y) * k} l")
        else:
            self.arc(
                xc + r * my_arc,
                yc - r,
                xc + r,
                yc - r * my_arc,
                xc + r,
                yc,
            )

        xc = x + w - r
        yc = y + h - r
        self._out(f"{(x + w) * k} {(hp - yc) * k} l")
        if "3" not in corners:
            self._out(f"{(x + w) * k} {(hp - (y + h)) * k} l")
        else:
            self.arc(
                xc + r,
                yc + r * my_arc,
                xc + r * my_arc,
                yc + r,
                xc,
                yc + r,
            )

        xc = x + r
        yc = y + h - r
        self._out(f"{xc * k} {(hp - (y + h)) * k} l")
        if "4" not in corners:
            self._out(f"{x * k} {(hp - (y + h)) * k} l")
        else:
            self.arc(
                xc - r * my_arc,
                yc + r,
                xc - r,
                yc + r * my_arc,
                xc - r,
                yc,
            )

        xc = x + r
        yc = y + r
        self._out(f"{x * k} {(hp - yc) * k} l")
        if "1" not in corners:
            self._out(f"{x * k} {(hp - y) * k} l")
            self._out(f"{(x + r) * k} {(hp - y) * k} l")
        else:
            self.arc(
                xc - r,
                yc - r * my_arc,
                xc - r * my_arc,
                yc - r,
                xc,
                yc - r,
            )
        self._out(op)

    def arc(self, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float):
        """
        Draws an arc.

        Args:
            x1 (float): The x-coordinate of the start point of the arc.
            y1 (float): The y-coordinate of the start point of the arc.
            x2 (float): The x-coordinate of the end point of the arc.
            y2 (float): The y-coordinate of the end point of the arc.
            x3 (float): The x-coordinate of the control point of the arc.
            y3 (float): The y-coordinate of the control point of the arc.
        """
        h = self.h
        self._out(
            f"""{x1 * self.k:.2f}
             {(h - y1) * self.k:.2f} {x2 * self.k:.2f}
            {(h - y2) * self.k:.2f} {x3 * self.k:.2f}
            {(h - y3) * self.k:.2f} c"""
        )


def add_formatted_page(pdf: pdf_generator) -> None:
    """Adds a formatted page to the PDF document.

    The page is filled with a light gray color and has a white rectangle in
    the center.
    The font is set to Arial, bold, size 18, and the fill color is set to
    white.

    Args:
        pdf: The PDF document to which the page is added.
    """
    pdf.set_fill_color(225, 230, 237)
    pdf.add_page()
    pdf.rect(0, 0, 210, 297, "F")
    pdf.set_font("Arial", "B", 18)
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(10, 10, 190, 277, "F")


def check_add_page(pdf: pdf_generator, text: str) -> list[str]:
    """Checks if the text overflows onto a new page and adds a new page if
      necessary.

    The text is split into lines based on the available page width.
    If the text overflows onto a new page, a new page is added and the text
    is continued on the new page.

    Args:
        pdf: The PDF document to which the text is added.
        text: The text to be added to the PDF document.

    Returns:
        A list of strings, where each page is a string containing the text
        that fits on that page.
    """

    pages: list[str] = []  # Store the text content for each page
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
