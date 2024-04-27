import vertexai
import functions_framework

from os import environ

from vertexai.language_models import TextGenerationModel

project_id = environ.get("PROJECT_ID")
PUBLIC_BUCKET = environ.get("PUBLIC_BUCKET")
TNC_IMAGE = environ.get("TNC_IMAGE")
FD_TNC_DOC = environ.get("FD_TNC_DOC")


@functions_framework.http
def generate_fd_confirmation_message(request):
    request_json = request.get_json(silent=True)

    print(request_json["sessionInfo"]["parameters"])

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]
    fd_amount = request_json["sessionInfo"]["parameters"]["fd_amount"]
    fd_tenure = request_json["sessionInfo"]["parameters"]["fd_tenure"]

    print(customer_id)
    print(fd_amount)
    print(fd_tenure)

    vertexai.init(project=project_id, location="us-central1")
    parameters = {
        "max_output_tokens": 512,
        "temperature": 0.3,
        "top_p": 0.8,
        "top_k": 40,
    }
    model = TextGenerationModel.from_pretrained("text-bison")

    response = model.predict(
        """
        Format the amount in the following information in indian rupee format(seprated by comma in in every 2 digits) and with 2 decimal places,e.g. ₹100000000 to ₹10,00,00,000.00
        {0}.
        The amount should be exact same as {0} just format it.
        Only the amount should be returned and not the entire code.
        Do not return the code.
        """.format(
            fd_amount
        ),
        **parameters,
    )

    print(response.text)

    confirmation_msg = (
        f"Please confirm that you want to invest {response.text} for"
        f" {fd_tenure}.\nMake sure you go through the following terms and"
        " conditions before proceeding."
    )

    print(confirmation_msg)

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

    print(res)

    return res
