import json
import os
import base64
from PIL import Image, ImageDraw
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content

# Still not secure!
def returnAPIKey(file_path="API_key.txt"):
  with open(file_path, "r") as f:
    api_key = f.read().strip()
  return api_key

def allowed_file(filename):
  return '.' in filename and \
    filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

def upload_image_genai(filename):
  image = genai.upload_file(filename, mime_type="image/png")
  return image

def call_determiner(user_photo):
  genai.configure(api_key= returnAPIKey())
  model = genai.GenerativeModel(model_name="gemini-1.5-pro-002",generation_config=determiner_config)
  response = model.generate_content([user_photo, "Determine if the image provided contains produce, the type of produce, and if there is more than 1 in the image"])
  return response.text



def rate_single_produce(produce_name, user_photo):
  genai.configure(api_key= returnAPIKey())
  model = genai.GenerativeModel(model_name="gemini-1.5-pro-002",generation_config=single_produce_config)
  response = model.generate_content([user_photo, single_produce_prompt])
  return response.text


def bulk_selector_produce(produce_name, user_photo):
  genai.configure(api_key= returnAPIKey())
  model = genai.GenerativeModel(model_name="gemini-1.5-pro-002",generation_config=bulk_selector_config)
  response = model.generate_content([user_photo, bulk_selector_prompt])
  return response.text


def extract_bulk_text_from_json(selector_json_string):
  selector_json = json.loads(selector_json_string)
  return selector_json["Describe Reasoning"]


def draw_box_image(selector_json_string, filename, export_location):
  selector_json = json.loads(selector_json_string)
  top_left = [int(selector_json["Top Left Coordinates"]["X Coordinate"]), int(selector_json["Top Left Coordinates"]["Y Coordinate"])]
  bottom_right = [int(selector_json["Bottom Right Coordinates"]["X Coordinate"]), int(selector_json["Bottom Right Coordinates"]["Y Coordinate"])]
  
  image = Image.open(filename)
  image.convert("RGB")
  draw = ImageDraw.Draw(image)
  if top_left[0] > bottom_right[0]:
    temp = top_left[0]
    top_left[0] = bottom_right[0]
    bottom_right[0] = temp
  if top_left[1] > bottom_right[1]:
    temp = top_left[1]
    top_left[1] = bottom_right[1]
    bottom_right[1] = temp 
  
  draw.rectangle((top_left[0], top_left[1], bottom_right[0], bottom_right[1]), outline="blue", width=10)
  draw.rectangle((10, 10, 100, 100), outline="green", width=10)

  new_file_name = "editted_photo" + ".png"
  count = 1
  new_file_location = os.path.join(export_location, new_file_name)
  while os.path.exists(new_file_location):
    new_file_name = "editted_photo_" + str(count) +".png"
    count = count + 1
    new_file_location = os.path.join(export_location, new_file_name)
  
  image.save(new_file_location)
  return new_file_name











bulk_selector_prompt = "Please identify the single best produce in the image. Then, select and provide the top left and bottom right coordinates of a bounding box for the highest quality produce in this image."


single_produce_prompt = """
You are a reasonable judge with deep knowledge of fruit and vegetable quality. Your task is to develop a rating for the selected produce in the image.

This rating system should be based on the following 3 prioritized criteria (in order of importance):

- Quality: Factors like size, shape, color, and firmness. (5 stars = excellent, 4 stars = very good, 3 stars = good, 2 stars = fair, 1 star = poor)
- Freshness: Indicators of peak ripeness and lack of spoilage. (5 stars = very fresh, 4 stars = fresh, 3 stars = slightly overripe, 2 stars = overripe, 1 star = very overripe)
- Absence of Defects: Freedom from blemishes, bruises, cuts, insect damage, and signs of disease. (5 stars = very few minor defects, 4 stars = few minor defects, 3 stars = minor defects, 2 stars = some minor and major defects, 1 star = many major defects)

Based on these criteria, use a star rating scale from 1 to 5 stars (5 being the highest rating, allowing for half stars; e.g. 3.5 Stars) for each of these categories and come up with an overall rating based on the previous ratings for the produce in the image.

Provide a concise paragraph giving your reasoning for the rating.

Additionally, provide a list of 'Pros' and 'Cons' in the form of concise strings offering practical tips on how shoppers can improve their produce selection skills. If the produce quality is low, make the pro into an indirect joke about otherways to use the produce.
"""






determiner_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_schema": content.Schema(
    type = content.Type.OBJECT,
    enum = [],
    required = ["is_produce", "more_than_one_produce","produce_name"],
    properties = {
      "is_produce": content.Schema(
        type = content.Type.BOOLEAN,
      ),
      "more_than_one_produce": content.Schema(
        type = content.Type.BOOLEAN,
      ),
      "produce_name": content.Schema(
        type = content.Type.STRING,
      ),
    },
  ),
  "response_mime_type": "application/json",
}



single_produce_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_schema": content.Schema(
    type = content.Type.OBJECT,
    enum = [],
    required = ["Freshness Rating", "Quality Rating", "Absence of Defects Rating", "Overall Rating", "Reasoning for Rating", "Pros of Produce Selected", "Cons of Produce Selected"],
    properties = {
      "Freshness Rating": content.Schema(
        type = content.Type.NUMBER,
      ),
      "Quality Rating": content.Schema(
        type = content.Type.NUMBER,
      ),
      "Absence of Defects Rating": content.Schema(
        type = content.Type.NUMBER,
      ),
      "Overall Rating": content.Schema(
        type = content.Type.NUMBER,
      ),
      "Reasoning for Rating": content.Schema(
        type = content.Type.STRING,
      ),
      "Pros of Produce Selected": content.Schema(
        type = content.Type.OBJECT,
        enum = [],
        required = ["First Pro"],
        properties = {
          "First Pro": content.Schema(
            type = content.Type.STRING,
          ),
          "Second Pro": content.Schema(
            type = content.Type.STRING,
          ),
          "Third Pro": content.Schema(
            type = content.Type.STRING,
          ),
        },
      ),
      "Cons of Produce Selected": content.Schema(
        type = content.Type.OBJECT,
        enum = [],
        required = ["First Con"],
        properties = {
          "First Con": content.Schema(
            type = content.Type.STRING,
          ),
          "Second Con": content.Schema(
            type = content.Type.STRING,
          ),
          "Third Con": content.Schema(
            type = content.Type.STRING,
          ),
        },
      ),
    },
  ),
  "response_mime_type": "application/json",
}


bulk_selector_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_schema": content.Schema(
    type = content.Type.OBJECT,
    enum = [],
    required = ["Top Left Coordinates", "Bottom Right Coordinates", "Describe Reasoning"],
    properties = {
      "Top Left Coordinates": content.Schema(
        type = content.Type.OBJECT,
        enum = [],
        required = ["X Coordinate", "Y Coordinate"],
        properties = {
          "X Coordinate": content.Schema(
            type = content.Type.INTEGER,
          ),
          "Y Coordinate": content.Schema(
            type = content.Type.INTEGER,
          ),
        },
      ),
      "Bottom Right Coordinates": content.Schema(
        type = content.Type.OBJECT,
        enum = [],
        required = ["X Coordinate", "Y Coordinate"],
        properties = {
          "X Coordinate": content.Schema(
            type = content.Type.INTEGER,
          ),
          "Y Coordinate": content.Schema(
            type = content.Type.INTEGER,
          ),
        },
      ),
      "Describe Reasoning": content.Schema(
        type = content.Type.STRING,
      ),
    },
  ),
  "response_mime_type": "application/json",
}