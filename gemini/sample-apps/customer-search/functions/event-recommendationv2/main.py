import os
from os import environ
import random
import string
import tempfile

import functions_framework
from google.cloud import bigquery, storage
import vertexai
from vertexai.language_models import TextGenerationModel
from vertexai.preview.vision_models import ImageGenerationModel

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def event_recommendation_v2(request):
    request_json = request.get_json(silent=True)
    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]
    print(request_json)
    bq_client = bigquery.Client()
    query_user_affinities = f"""
        SELECT Affinities FROM `{project_id}.DummyBankDataset.Customer`
        WHERE customer_id = {customer_id}
    """
    query_event_details = """
        SELECT * FROM `{project_id}.DummyBankDataset.CustomerEvents`
    """
    result_user_affinities = bq_client.query(query_user_affinities)
    result_event_details = bq_client.query(query_event_details)

    for row in result_user_affinities:
        print(row)
        if row["Affinities"] is not None:
            user_affinities = row["Affinities"].split(",")
    for i in range(len(user_affinities)):
        user_affinities[i] = user_affinities[i].lower().strip()
    print(user_affinities)

    event_recommended = None

    # ASSUMPTION: There exists an event which always matches the user affinities - wrong assumption but will handle that case later
    for row in result_event_details:
        print(row)
        event_tags = row["event_tags_"].split(",")
        print(event_tags)
        for i in range(len(event_tags)):
            event_tags[i] = event_tags[i].lower().strip()
        for tag in event_tags:
            if tag in user_affinities:
                event_recommended = row
                break
        if event_recommended is not None:
            break

    print(event_recommended)

    vertexai.init(project=project_id, location="us-central1")
    model_prompt = TextGenerationModel.from_pretrained("text-bison@001")
    parameters = {
        "max_output_tokens": 1024,
        "temperature": 0.2,
        "top_p": 0.95,
        "top_k": 40,
    }
    response = model_prompt.predict(
        """
    You are a graphic designer and need to create prompts to generate image invite for events.

    Describe in detail the image content, art style, viewpoint, framing, lighting, colour scheme .

    Do not include human.
    The image is meant to be shown on a mobile screen.
    There should be no text/writing in the image.

    Example:

    Input: Create a prompt to generate image invite for a golfing event called Golf Day.
    Output: Art style: Realistic with a touch of impressionism
    Viewpoint: Bird's eye view
    Framing: Close-up on a lush green golf course, with rolling hills, manicured fairways, and sparkling bunkers. The sun is setting in the background, casting a warm glow over the scene.
    Color scheme: Shades of green, gold, and orange

    Additional details:

    A golf flag blowing gently in the breeze
    A lone golf ball resting on the green
    A pair of golf clubs crossed over each other
    A winding path leading through the trees
    A distant view of the clubhouse
    Mobile optimization:

    The image should be cropped to a 16:9 aspect ratio
    The focal point of the image should be placed in the center of the frame
    The image should be high-resolution and visually appealing
    Overall impression:

    The image should convey a sense of elegance, sophistication, and excitement. It should be inviting and encourage viewers to learn more about the Golf Day event.


    Input: Create a prompt to generate invite image for a Party event called DJ-Night . Do not include humans in the image.
    Output: Art style: Abstract, geometric shapes with vibrant colors
    Viewpoint: Looking up at the DJ booth from the dance floor
    Framing: Close-up of the DJ booth, with the DJ and their equipment in the center of the frame. The dance floor and crowd are visible in the background.
    Lighting: Dark and moody, with spotlights focused on the DJ and the dance floor.
    Color scheme: Neon colors, with a focus on blues and purples.
    Additional details:

    A large disco ball hanging from the ceiling
    A fog machine creating a hazy atmosphere
    Laser lights shooting across the dance floor
    A crowd of people dancing and enjoying the music
    Mobile optimization:

    The image should be cropped to a 16:9 aspect ratio
    The focal point of the image should be placed in the center of the frame
    The image should be high-resolution and visually appealing
    Overall impression:

    The image should convey a sense of excitement, energy, and fun. It should be inviting and encourage viewers to come to the DJ-Night event.


    Create a prompt to generate invite image for a {1} event called {0} . Do not include humans in the image.
    """.format(
            event_recommended["event_name_"], event_recommended["event_type"]
        ),
        **parameters,
    )
    print(response.text)
    model = ImageGenerationModel.from_pretrained("imagegeneration@002")
    response = model.generate_images(
        prompt=response.text,
        # Optional:
        number_of_images=1,
        seed=0,
    )

    image_file_name = (
        "".join(
            random.choices(
                string.ascii_uppercase + string.digits + string.ascii_lowercase,
                k=20,
            )
        )
        + ".png"
    )
    image_dir = os.path.join(tempfile.gettempdir(), "generated-image")
    image_path = os.path.join(image_dir, image_file_name)
    output_bucket = "public_bucket_fintech_app"

    if not os.path.isdir(image_dir):
        os.mkdir(image_dir)

    print("Image dir = ", image_dir)
    print("Image path = ", image_path)
    print("Image file_name = ", image_file_name)

    response[0].save(image_path)

    gcs_client = storage.Client()
    bucket = gcs_client.bucket(output_bucket)
    generated_image = bucket.blob(image_file_name)
    generated_image.upload_from_filename(image_path)

    print(type(response[0]))
    print(response[0])
    rawUrl = "https://storage.googleapis.com/" + output_bucket + "/" + image_file_name

    response2 = model_prompt.predict(
        """
    You are CymBuddy , a chatbot of Cymbal Bank. You need to recommend an event to the user because their account status is healthy. The user's interests are {6}. You choose to recommend the following event because the event tags matched one or more of the user's interests:
    Event name: {0}
    event date: {1}
    event type: {2}
    event tags: {3}
    location: {4}
    last date to register: {5}

    Create a message inviting the user to the event.  The tone should be friendly and conversational. Do not greet the user, that is, do not say hi or hey.

    Example:
    You are CymBuddy , a chatbot of Cymbal Bank. You need to recommend an event to the user because their account status is healthy. The user's interests are Classical Music, Golf, Hiking, Real Estate. You choose to recommend the following event because the event tags matched one or more of the user's interests:
    Event name: Golf Day
    event date: 2023-10-31
    event tags: Golf, Networking
    location: Golfshire
    last date to register: 2023-10-21



Heads up, golf enthusiast! ⛳️

We noticed you're a fan of the green, so we thought you might be interested in the upcoming Golf Day event on October 31st at Golfshire.

It's a great opportunity to network with other golf aficionados and enjoy a day of friendly competition. Plus, there'll be plenty of opportunities to learn from experts and improve your game.

Registration closes on October 21st, so don't miss out! 🏌️‍♀️🏌️‍♂️

    """.format(
            event_recommended["event_name_"],
            event_recommended["event_date_"],
            event_recommended["event_type"],
            event_recommended["event_tags_"],
            event_recommended["location"],
            event_recommended["last_date_of_invite_"],
            user_affinities,
        ),
        **parameters,
    )
    print(response2.text)

    custom_payload = {
        "payload": {
            "richContent": [
                [
                    {
                        "type": "image",
                        "rawUrl": rawUrl,
                        "accessibilityText": response2.text,
                    }
                ]
            ]
        }
    }
    # {"text": {"text": [text]}}
    invitation = {
        "text": {
            "text": [response2.text],
        }
    }
    print(custom_payload)
    res = {"fulfillment_response": {"messages": [invitation, custom_payload]}}
    print(res)
    return res
