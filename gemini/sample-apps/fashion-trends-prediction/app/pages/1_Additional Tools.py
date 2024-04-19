from config import config
from utilities import add_logo, render_svg

add_logo(config["Images"]["logo"])

# Set the path to the local image file
image_path = config["Images"]["additional_tools"]

# Read the SVG image as a string
with open(image_path, "r") as f:
    svg = f.read()

render_svg(svg)
