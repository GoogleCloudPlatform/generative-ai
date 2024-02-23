from PIL import Image, ImageColor, ImageFont, ImageDraw


def add_logo(image, logo_path, corner, padding):
    """Adds the  logo to one of the corners of an image."""

    # Load the  logo image.
    logo = Image.open(logo_path)

    # Resize the  logo image to be 10% of the image height.
    logo = logo.resize((int(image.height * 0.1), int(image.height * 0.1)))

    # Add the  logo image to the specified corner of the original image.
    if corner == "top left":
        image.paste(logo, (padding, padding), logo)
    elif corner == "top right":
        image.paste(logo, (image.width - logo.width - padding, padding), logo)
    elif corner == "bottom left":
        image.paste(logo, (padding, image.height - logo.height - padding), logo)
    elif corner == "bottom right":
        image.paste(
            logo,
            (image.width - logo.width - padding, image.height - logo.height - padding),
            logo,
        )


def add_text(image, text, font_path, font_size, color, position):
    """Adds text to an image using Markdown."""

    # Create a new image that is the same size as the original image.
    new_image = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(new_image)

    # Create a font object.
    font = ImageFont.truetype(font_path, font_size)

    # Draw the text on the new image.
    draw.text(position, text, font=font, fill=color)

    # Add the new image to the original image as a mask.
    image.paste(new_image, (0, 0), new_image)


def run_pipeline(
    image_path,
    output_path,
    logo_path,
    corner,
    padding,
    text,
    font_path,
    font_size,
    color,
    position,
    **kwargs
):
    """Creates a output image using the PIL library."""

    # Load the image.
    image = Image.open(image_path)

    # Add the  logo to the image.
    add_logo(image, logo_path, corner, padding)

    # Add the text to the image.
    add_text(image, text, font_path, font_size, color, position)

    # Save the image as a PNG with transparency.
    image.save(output_path, "PNG")

    return image
