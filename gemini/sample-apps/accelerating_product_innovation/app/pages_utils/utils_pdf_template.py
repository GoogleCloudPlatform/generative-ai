"""
Class for generating a pdf template for exporting content and emails.
"""

from math import sqrt

import fpdf


class PDFRounded(fpdf.FPDF):
    """
    Initializes basic PDF template for email and content files
    """

    def rounded_rect(self, x, y, w, h, r, style="", corners="1234"):
        """
        Draws a rectangle with rounded corners.

        Args:
            x (float): The x-coordinate of the top-left corner of the rectangle.
            y (float): The y-coordinate of the top-left corner of the rectangle.
            w (float): The width of the rectangle.
            h (float): The height of the rectangle.
            r (float): The radius of the rounded corners.
            style (str, optional): The style of the rectangle.
            Can be 'F' for filled, 'FD' for filled and drawn,
            or 'DF' for drawn and filled. Defaults to 'S' for stroked.
            corners (str, optional): A string of characters indicating
            which corners of the rectangle should be rounded.
            Can be '1234' for all corners, '12' for the top-left and top-right corners,
            '34' for the bottom-left and bottom-right corners, or
            '13' for the top-left and bottom-right corners. Defaults to '1234'.
        """

        k = self.k
        hp = self.h
        if style == "F":
            op = "f"
        elif style == "FD" or style == "DF":
            op = "B"
        else:
            op = "S"
        my_arc = 4 / 3 * (sqrt(2) - 1)
        self._out("%.2F %.2F m" % ((x + r) * k, (hp - y) * k))

        xc = x + w - r
        yc = y + r
        self._out("%.2F %.2F l" % (xc * k, (hp - y) * k))
        if "2" not in corners:
            self._out("%.2F %.2F l" % ((x + w) * k, (hp - y) * k))
        else:
            self._arc(
                xc + r * my_arc,
                yc - r,
                xc + r,
                yc - r * my_arc,
                xc + r,
                yc,
            )

        xc = x + w - r
        yc = y + h - r
        self._out("%.2F %.2F l" % ((x + w) * k, (hp - yc) * k))
        if "3" not in corners:
            self._out(
                "%.2F %.2F l" % ((x + w) * k, (hp - (y + h)) * k)
            )
        else:
            self._arc(
                xc + r,
                yc + r * my_arc,
                xc + r * my_arc,
                yc + r,
                xc,
                yc + r,
            )

        xc = x + r
        yc = y + h - r
        self._out("%.2F %.2F l" % (xc * k, (hp - (y + h)) * k))
        if "4" not in corners:
            self._out("%.2F %.2F l" % (x * k, (hp - (y + h)) * k))
        else:
            self._arc(
                xc - r * my_arc,
                yc + r,
                xc - r,
                yc + r * my_arc,
                xc - r,
                yc,
            )

        xc = x + r
        yc = y + r
        self._out("%.2F %.2F l" % (x * k, (hp - yc) * k))
        if "1" not in corners:
            self._out("%.2F %.2F l" % (x * k, (hp - y) * k))
            self._out("%.2F %.2F l" % ((x + r) * k, (hp - y) * k))
        else:
            self._arc(
                xc - r,
                yc - r * my_arc,
                xc - r * my_arc,
                yc - r,
                xc,
                yc - r,
            )
        self._out(op)

    def _arc(self, x1, y1, x2, y2, x3, y3):
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
