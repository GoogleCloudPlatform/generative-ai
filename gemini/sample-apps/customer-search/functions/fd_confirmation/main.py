# pylint: disable=E0401

from os import environ

import functions_framework

from utils.gemini import Gemini

project_id = environ.get("PROJECT_ID")
PUBLIC_BUCKET = environ.get("PUBLIC_BUCKET")
TNC_IMAGE = environ.get("TNC_IMAGE")
FD_TNC_DOC = environ.get("FD_TNC_DOC")


@functions_framework.http
def generate_fd_confirmation_message(request):
    """
    Generates a confirmation message for a fixed deposit.

    Args:
        request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    request_json = request.get_json(silent=True)

    fd_amount = request_json["sessionInfo"]["parameters"]["fd_amount"]
    fd_tenure = request_json["sessionInfo"]["parameters"]["fd_tenure"]

    model = Gemini()
    response = model.generate_response(
        f"""
        Format the amount in the following information in indian rupee format
        (seprated by comma in in every 2 digits) and with 2 decimal places,e.g. ₹100000000 to ₹10,00,00,000.00
        {fd_amount}.
        The amount should be exact same as {fd_amount} just format it.
        Only the amount should be returned and not the entire code.
        Do not return the code.
        """
    )

    confirmation_msg = (
        f"Please confirm that you want to invest {response} for"
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
                                                )
                                            },
                                            "anchor": {
                                                "href": (
                                                    "https://storage.googleapis.com/"
                                                    + PUBLIC_BUCKET
                                                    + "/"
                                                    + FD_TNC_DOC
                                                )  # replace with own T&C doc name
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
