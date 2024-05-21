"""This is a python utility file."""

# pylint: disable=E0401
# pylint: disable=R0801
# pylint: disable=R0914

import os
from os import environ
import random
import string
import tempfile

from PIL import Image
import functions_framework
from google.cloud import storage
from utils.bq_query_handler import BigQueryHandler
from utils.gemini import Gemini
from vertexai.preview.vision_models import ImageGenerationModel

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def travel_event_recommendation(request):
    """
    Recommends an event to the user based on their interests and travel plans.

    Args:
        request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    request_json = request.get_json(silent=True)

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]
    city = request_json["sessionInfo"]["parameters"]["city"]
    country = request_json["sessionInfo"]["parameters"]["country"]
    start_date = request_json["sessionInfo"]["parameters"]["start_date"]
    end_date = request_json["sessionInfo"]["parameters"]["end_date"]

    query_handler = BigQueryHandler(customer_id=customer_id)

    result_user_affinities = query_handler.query("query_user_affinities")

    for row in result_user_affinities:
        if row["Affinities"] is not None:
            user_affinities = row["Affinities"].split(",")
    for i in enumerate(user_affinities):
        user_affinities[i] = user_affinities[i].lower().strip()

    model = Gemini()

    trip_event_recommendation_prompt = f"""
You are CymBuddy, a bot for Cymbal Bank. You need to recommend an event to the user
based on their interests which they can enjoy on their upcoming trip.


Recommend only one event.
Tell the user that it is complimentary or at a discounted price.
Do not greet the user as the recommendation is part of an ongoing conversation.
The tone should be friendly and conversational.
Advise the user to book the tickets for the event.
Be brief, do not exceed 10 lines.
Make sure the event falls within the duration of their trip.
Make sure the event is being held at/near the travel destination.


Input:
The user is travelling to Dubai, United Arab Emirates from 21st Jan 2024 to 14th Fen 2024.
The user is interested in Classical Music, Golf, Hiking, Real Estate.

Ouput:
Also, I found a golf event in Dubai, UAE that you might enjoy during your upcoming trip:

OMEGA Dubai Desert Classic
January 26-29, 2024
Emirates Golf Club

This event is one of the most prestigious golf tournaments on the DP World Tour,
with a field of some of the best players in the world.
Simply show your Cymbal Bank card at the ticket office when you arrive for
your complimentary ticket. Have a wonderful trip!


Input:
The user is travelling to Dubai, United Arab Emirates from 21st Jan 2024 to 14th Fen 2024.
The user is interested in Classical Music, Golf, Hiking, Real Estate.

Output:
I found a classical music event that you might enjoy during your trip to Dubai:

Dubai Opera Presents: The Little Prince
January 26-28, 2024
Dubai Opera

This imaginative adaptation of Antoine de Saint-Exupéry's timeless classic features a talented
cast of international performers, mesmerizing visuals, and a captivating score.

Simply enter your Cymbal Bank card number at the checkout to book your complimentary ticket.
Have a wonderful trip!

Input:
The user is travelling to Manilla, Phillipines from 21st Jan 2024 to 14th Fen 2024.
The user is interested in Classical Music, Golf, Hiking, Real Estate.

Output:
Since you are interested in classical music, I highly recommend attending the
Manila Symphony Orchestra's Season Opening Concert happening on January 25, 2024
at the Cultural Center of the Philippines.

Tickets are now available at a 20% discount for all Cymbal Bank cardholders.
Just use the code CYMBAL20 upon checkout. I hope you have a wonderful time in Manila!


Input:
The user is travelling to {city}{country} from {start_date} to {end_date}.
The user is interested in {user_affinities}.

Output:



"""

    response = model.generate_response(trip_event_recommendation_prompt)

    find_event_type_prompt = f"""
    What is the type of event in the following invite?


    Example:

    Input:
    Since you are interested in classical music, I highly recommend attending the
    Manila Symphony Orchestra's Season Opening Concert happening on January 25, 2024
    at the Cultural Center of the Philippines.

    Tickets are now available at a 20% discount for all Cymbal Bank cardholders.
    Just use the code Cymbal20 upon checkout.

    You can book your tickets here: [link to event website]

    I hope you have a wonderful time in Manila!

    Output: Orchestra

    Input:
    Since you are interested in classical music, I highly recommend attending the Madrid
    Philharmonic Orchestra's concert at the Teatro Real on January 27, 2024.

    The concert will feature a performance of Beethoven's Symphony No. 9, one of the most famous
    and beloved pieces of classical music.

    As a Cymbal Bank customer, you are eligible for a complimentary ticket to this event.
    Simply show your Cymbal Bank card at the box office when you book your ticket.

    I hope you have a wonderful time in Madrid!

    Output: Orchestra



    Input:
    Also, I found a golf event in Dubai, UAE that you might enjoy during your upcoming trip
    on January 21st to February 14th:

    OMEGA Dubai Desert Classic
    January 26-29, 2024
    Emirates Golf Club

    This event is one of the most prestigious golf tournaments on the DP World Tour,
    with a field of some of the best players in the world.

    As a Cymbal Bank customer, you are eligible for a complimentary ticket to this event.
    Simply show your Cymbal Bank card at the ticket office when you arrive.

    Output: Golf

    Input:
    I found a classical music event that you might enjoy during your trip to Dubai:

    Dubai Opera Presents: The Little Prince
    January 26-28, 2024
    Dubai Opera

    This imaginative adaptation of Antoine de Saint-Exupéry's timeless classic features a
    talented cast of international performers, mesmerizing visuals, and a captivating score.

    You can avail a complimentary ticket to this event. Simply enter your Cymbal Bank card
    number at the checkout when you book your ticket.

    Have a wonderful trip!

    Output: Opera

    Input:
    Since you are interested in classical music, I would recommend checking out the Dubai Opera.
    They have a variety of performances scheduled during your trip, including an opera and a ballet.

    You can book tickets online or at the box office.

    As a Cymbal Bank customer, you can get a 10% discount on tickets. Just use the promo code
    CYMBAL10 when you book your tickets.

    Output: Opera

    Input:
    The Singapore Symphony Orchestra is performing Beethoven's 9th Symphony on January 28th
    at the Esplanade Concert Hall.

    Your Cymbal Bank card gets you 2-for-1 tickets.

    Ouput: Orchestra

    Input:
    {response}

    Output:

    """
    response2 = model.generate_response(find_event_type_prompt)

    create_image_for_invite_prompt = f"""
    You are a graphic designer and need to create prompts to generate image invite for events.

    Describe in detail the image content, art style, viewpoint, framing, lighting, colour scheme .

    The image is meant to be shown on a mobile screen.
    There should be no humans in the image.
    There should be no text/writing in the image.
    Do not use the name of any artist or composer or author.

    Example:

    Input: Create a prompt to generate image invite for a golfing event. There should be no humans.
    Output: Art style: Realistic with a touch of impressionism
    Viewpoint: Bird's eye view
    Framing: Close-up on a lush green golf course, with rolling hills, manicured fairways, and
    sparkling bunkers. The sun is setting in the background, casting a warm glow over the scene.
    Color scheme: Shades of green, gold, and orange

    Additional details:

    A golf flag blowing gently in the breeze
    A lone golf ball resting on the green
    A pair of golf clubs crossed over each other
    A winding path leading through the trees
    A distant view of the clubhouse
    Mobile optimization:
    The focal point of the image should be placed in the center of the frame
    The image should be high-resolution and visually appealing


    Input:Create a prompt to generate invite image for a Opera event.
    There should be no humans in the image.
Output: Art style: Surrealism Viewpoint: Aerial view Framing: A view of an opera house from above,
with the stage and orchestra pit in the foreground. The audience is represented by a
sea of empty seats. Color scheme: Dark and moody, with pops of color from the stage lights.
Additional details:  A spotlight shining down on the empty stage A grand piano on the stage A
conductor's podium in front of the orchestra pit Rows of empty seats in the audience A chandelier
hanging from the ceiling Mobile optimization: The focal point of the image should be placed in
the center of the frame The image should be high-resolution and visually appealing

    Input: Create a prompt to generate invite image for a {response2} event.
    There should be no humans in the image.
    Output:
    """

    response3 = model.generate_response(create_image_for_invite_prompt)

    model = ImageGenerationModel.from_pretrained("imagegeneration@005")
    response = model.generate_images(
        prompt=response3,
        # Optional:
        negative_prompt="""3D
absent limbs
age spot
additional appendages
additional digits
additional limbs
altered appendages
amputee
asymmetric
asymmetric ears
bad anatomy
bad ears
bad eyes
bad face
bad proportions
beard (optional)
broken finger
broken hand
broken leg
broken wrist
cartoon
childish (optional)
cloned face
cloned head
collapsed eyeshadow
combined appendages
conjoined
copied visage
corpse
cripple
cropped head
cross-eyed
depressed
desiccated
disconnected limb
disfigured
dismembered
disproportionate
double face
duplicated features
eerie
elongated throat
excess appendages
excess body parts
excess extremities
extended cervical region
extra limb
fat
flawed structure
floating hair (optional)
floating limb
four fingers per hand
fused hand
group of people
gruesome
high depth of field
immature
imperfect eyes
incorrect physiology
kitsch
lacking appendages
lacking body
long body
macabre
malformed hands
malformed limbs
mangled
mangled visage
merged phalanges
missing arm
missing leg
missing limb
mustache (optional)
nonexistent extremities
old
out of focus
out of frame
parched
plastic
poor facial details
poor morphology
poorly drawn face
poorly drawn feet
poorly drawn hands
poorly rendered face
poorly rendered hands
six fingers per hand
skewed eyes
skin blemishes
squint
stiff face
stretched nape
stuffed animal
surplus appendages
surplus phalanges
surreal
ugly
unbalanced body
unnatural
unnatural body
unnatural skin
unnatural skin tone
weird colors""",
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

    response[0].save(image_path)

    im = Image.open(image_path)
    new_im = im.resize((200, 200))
    new_im.save(image_path)

    gcs_client = storage.Client()
    bucket = gcs_client.bucket(output_bucket)
    generated_image = bucket.blob(image_file_name)
    generated_image.upload_from_filename(image_path)

    raw_url = "https://storage.googleapis.com/" + output_bucket + "/" + image_file_name

    custom_payload = {
        "payload": {
            "richContent": [
                [
                    {
                        "type": "image",
                        "rawUrl": raw_url,
                        "accessibilityText": response2,
                        "df-messenger-image-border-radius": 5,
                    }
                ]
            ]
        }
    }
    invitation = {
        "text": {
            "text": [response2],
        }
    }
    res = {"fulfillment_response": {"messages": [invitation, custom_payload]}}
    return res
