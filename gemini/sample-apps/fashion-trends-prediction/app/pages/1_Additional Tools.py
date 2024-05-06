"""
Module for the "Additional Tools" page of the fashion trends prediction app.
"""

from config import config
from utilities import add_logo, render_svg

add_logo(config["Images"]["logo"])

render_svg(config["Images"]["additional_tools"])
