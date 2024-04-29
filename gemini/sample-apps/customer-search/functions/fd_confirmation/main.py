from os import environ

import functions_framework
import vertexai
from vertexai.generative_models import FinishReason, GenerativeModel, Part
import vertexai.preview.generative_models as generative_models

project_id = environ.get("PROJECT_ID")
PUBLIC_BUCKET = environ.get("PUBLIC_BUCKET")
TNC_IMAGE = environ.get("TNC_IMAGE")
FD_TNC_DOC = environ.get("FD_TNC_DOC")


@functions_framework.http
def generate_fd_confirmation_message(request):
    request_json = request.get_json(silent=True)

    fd_amount = request_json["sessionInfo"]["parameters"]["fd_amount"]
    fd_tenure = request_json["sessionInfo"]["parameters"]["fd_tenure"]

    vertexai.init(project=project_id, location="us-central1")
    generation_config = {
        "max_output_tokens": 2048,
        "temperature": 1,
        "top_p": 1,
    }
    safety_settings = {
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }
    model = model = GenerativeModel("gemini-1.0-pro-002")
    responses = model.generate_content(
        f"""
        Format the amount in the following information in indian rupee format(seprated by comma in in every 2 digits) and with 2 decimal places,e.g. ₹100000000 to ₹10,00,00,000.00
        {fd_amount}.
        The amount should be exact same as {fd_amount} just format it.
        Only the amount should be returned and not the entire code.
        Do not return the code.
        """,
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    final_response = ""
    for response in responses:
        final_response += response.text

    confirmation_msg = (
        f"Please confirm that you want to invest {final_response} for"
        f" {fd_tenure}.\nMake sure you go through the following terms and"
        " conditions before proceeding."
    )

    res = {
        "fulfillment_response": {
            "messages": [
                {"text": {"text": [confirmation_msg]}},
                {
                    "payload": {
                        "richContent": [
                            [
                                {
                                    "type": "chips",
                                    "options": [
                                        {
                                            "text": "Terms and Conditions",
                                            "image": {
                                                "rawUrl": (
                                                    "https://storage.googleapis.com/"
                                                    + PUBLIC_BUCKET
                                                    + "/"
                                                    + TNC_IMAGE
                                                )  # tnc.jpeg" #can replace with image name to show with terms and conditions
                                            },
                                            "anchor": {
                                                "href": (
                                                    "https://storage.googleapis.com/"
                                                    + PUBLIC_BUCKET
                                                    + "/"
                                                    + FD_TNC_DOC
                                                )  # FD_TnC.pdf" #replace with own T&C doc name
                                            },
                                        }
                                    ],
                                }
                            ]
                        ]
                    }
                },
            ]
        },
        "sessionInfo": {
            "parameters": {
                "fd_amount": fd_amount,
            }
        },
    }

    return res
