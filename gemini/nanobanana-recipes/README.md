# Nano Banana 🍌: Gemini 2.5 Flash Image Recipes

[![GitHub license](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/nanobanana-recipes/LICENSE)

**Author: [Chouaieb Nemri](https://github.com/cnemri)**

Welcome to the Nano Banana Recipes repository! This collection provides a comprehensive set of examples and best practices for using Google's Gemini 2.5 Flash Image model (codename: Nano Banana) for a wide range of image generation and editing tasks.

Each recipe is a self-contained Python script that demonstrates a specific capability of the model. The scripts are designed to be clear, easy to understand, and reusable for your own projects. Common functionalities have been abstracted into a `utils` module to keep the recipe code clean and focused.

## How to Use

This project uses `uv` for Python package and environment management.

1.  **Set up your environment:**
    - Install `uv`: Follow the official [installation instructions](https://github.com/astral-sh/uv).
    - Create a virtual environment: `uv venv`
    - Activate the environment: `source .venv/bin/activate`
    - Install dependencies: `uv sync`

2.  **Configure your environment:**
    - Create a `.env` file by copying the example: `cp .env.example .env`
    - Edit the `.env` file and add your Google Cloud Project ID.

3.  **Add assets:** For recipes that require input images, place your images in the corresponding `assets` sub-directory.

4.  **Run a recipe:** Execute any of the Python scripts using `uv run`. Outputs will be saved to the `outputs` directory.

---

## The Recipes

### 1. Generate Image from Scratch
**Prompt:** `"A futuristic cityscape at sunset, with flying cars and towering, glowing skyscrapers."`
**Run:** `uv run python 1_generate_from_scratch.py`
| Input | Output |
| :---: | :----: |
| *Text Prompt Only* | ![Output](outputs/1_from_scratch.png) |

### 2. Aspect Ratio Control
**Prompt:** `"A cinematic, wide-angle shot of a lone astronaut standing on a desolate alien planet, looking up at a swirling, colorful nebula. The planet's surface is rocky and red, and two moons are visible in the sky. Render this scene on the provided canvas to match its 16:9 aspect ratio."`
**Run:** `uv run python 2_aspect_ratio_control.py`
| Input | Output |
| :---: | :----: |
| *Generated 16:9 Canvas* | ![Output](outputs/2_aspect_ratio.png) |

### 3. Image Outpainting
**Prompt:** `"This is a creative outpainting task. Take the provided source image and seamlessly extend it to fill the entire blank canvas. The new areas should logically and stylistically continue the scene from the original image. Imagine what might exist just beyond the borders of the original photo and bring it to life."`
**Run:** `uv run python 3_image_outpainting.py`
| Input | Output |
| :---: | :----: |
| ![Input](assets/3_image_outpainting/source_image.png) | ![Output](outputs/3_outpainting.png) |

### 4. Image Editing
**Prompt:** `"Please add a red bow tie and a black top hat to the person in the image. Change the background to an elegant ballroom setting with chandeliers and ornate decorations. Ensure the additions look natural and blend seamlessly with the original image."`
**Run:** `uv run python 4_image_editing.py`
| Input | Output |
| :---: | :----: |
| ![Input](assets/4_image_editing/image_to_edit.png) | ![Output](outputs/4_edited_image.png) |

### 5. Style Transfer
**Prompt:** `"Turn this into a Vincent Vahn Gogh style painting."`
**Run:** `uv run python 5_style_transfer.py`
| Content Input | Output |
| :---: | :----: |
| ![Content Input](assets/5_style_transfer/content_image.png) | ![Output](outputs/5_style_transfer.png) |

### 6. Photo Restoration
**Prompt:** `"Restore and recolor this old photograph as if it was taken by a modern digital camera. Your output shall solely be extracted photograph. ignore surroundings and fill all canvas by the photograph"`
**Run:** `uv run python 6_photo_restoration.py`
| Input | Output |
| :---: | :----: |
| ![Input](assets/6_photo_restoration/damaged_photo.png) | ![Output](outputs/6_restored_photo.png) |

### 7. Multiple Reference Images
**Prompt:** `"List all elements of the provided images, then create a new image that combines those elements into a consistent bedroom scene. Use empty bedroom as base preserving its camera angle. Render the final result on the provided blank canvas to ensure a 16:9 aspect ratio."`
**Run:** `uv run python 7_multiple_references.py`
| Input | Output |
| :---: | :----: |
| ![Input](assets/7_multiple_references/items.png) | ![Output](outputs/7_multiple_references.png) |

### 8. Virtual Try-On
**Prompt:** `"Take the garment from the second image and realistically place it on the person in the first image. Adjust the fit, lighting, and shadows to make it look natural."`
**Run:** `uv run python 8_virtual_try_on.py`
| Model Input | Garment Input | Output |
| :---: | :---: | :----: |
| ![Model Input](assets/8_virtual_try_on/model.png) | ![Garment Input](assets/8_virtual_try_on/garment.png) | ![Output](outputs/8_virtual_try_on.png) |

### 9. Product Recontextualization
**Prompt:** `"Take the product in this image and place it in a professionally styled kitchen setting, on a marble countertop next to a window with soft, natural light. The final image should look like a high-end advertisement."`
**Run:** `uv run python 9_product_recontext.py`
| Input | Output |
| :---: | :----: |
| ![Input](assets/9_product_recontext/product.png) | ![Output](outputs/9_product_recontext.png) |

### 10. Images with Text
**Prompt:** `"""
    Create a Pizzeria menu with the following content:
    The Artisan Crust Pizzeria
    Crafted Pizza, Simply Delicious.
    Our Signature Pizzas
    Classic Margherita - $11 / $17
    San Marzano tomato, fresh mozzarella, basil.
    Spicy Pepperoni - $12 / $18
    Tomato sauce, mozzarella, premium pepperoni.
    Garden Veggie - $12 / $19
    Tomato sauce, mozzarella, bell peppers, onion, mushrooms, olives.
    Smoky BBQ Chicken - $13 / $19
    BBQ sauce base, grilled chicken, mozzarella, red onion.
    Beverages
    Fountain Soda - $3
    Coca-Cola, Diet Coke, Sprite, Root Beer.
    Bottled Water - $3
    Still or Sparkling.
    Order Online or Call: 555-123-4567
    """`
**Run:** `uv run python 10_images_with_text.py`
| Input | Output |
| :---: | :----: |
| *Text Prompt Only* | ![Output](outputs/10_images_with_text.png) |

### 11. Character Consistency
**Prompt:** A series of prompts are used to generate the character in different scenarios, e.g., `"The character is US president signing Artificial Intelligence Act act and showing it to the camera"`
**Run:** `uv run python 11_character_consistency.py`
| Input | Output |
| :---: | :----: |
| ![Input](assets/11_character_consistency/reference.png) | ![Output](outputs/11_character_consistency_collage.png) |

### 12. Shifting Camera Perspective
**Prompt:** `"aerial perspective of a camera looking down at the stressed candidate"`
**Run:** `uv run python 12_shifting_camera_perspective.py`
| Input | Output |
| :---: | :----: |
| ![Input](assets/12_shifting_camera_perspective/original.png) | ![Output](outputs/12_camera_perspective.png) |

---

## Community Examples

For more inspiring examples and projects from the community, check out the Awesome Nano Banana Images repository:
[**Explore Community Examples on GitHub**](https://github.com/PicoTrex/Awesome-Nano-Banana-images/blob/main/README_en.md)
