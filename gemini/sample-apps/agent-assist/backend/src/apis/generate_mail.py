"""This is a python utility file."""

# pylint: disable=E0401

from flask import jsonify, request
from utils.mail import Mail
from utils.text_bison import TextBison

PROMPT_TO_GENERATE_MAIL = """
    Generate a professional email for me. for the given query: {query}
    """

PROMPT_TO_GET_SUBJECT = """
    Extract the subject from the email and return only the subject
    email: {email}
    """

PROMPT_TO_GET_BODY = """
    Extract the body from the email and return only the body
    email: {email}
    """

tb = TextBison()


def generate_mail() -> tuple[dict, int]:
    """
    Generates a professional email based on the given query.

    Returns:
        dict: A dictionary containing the generated email.
    """
    text_to_generate = request.json.get("inputText")
    try:
        response = tb.generate_response(
            PROMPT_TO_GENERATE_MAIL.format(query=text_to_generate)
        )
        return jsonify({"generatedMail": response}), 200
    except ValueError as e:
        return (
            jsonify(
                {
                    "error": str(e),
                    "generatedMail": "Unable to generate mail at the momment",
                }
            ),
            400,
        )


def extract_and_send_mail() -> tuple[dict, int]:
    """
    Extracts the subject and body from the generated email and sends the email
    to the given email address.

    Returns:
        dict: A dictionary containing a message indicating whether
            the email was sent successfully.
    """
    generated_mail = request.json.get("generatedMail")
    email_id = request.json.get("emailId")
    subject = tb.generate_response(PROMPT_TO_GET_SUBJECT.format(email=generated_mail))
    body = tb.generate_response(PROMPT_TO_GET_BODY.format(email=generated_mail))
    mail = Mail()
    mail.send_email(email_id, subject, body)
    return jsonify({"message": "Email sent successfully"}), 200
