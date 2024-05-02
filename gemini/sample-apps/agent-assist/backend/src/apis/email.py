"""This is a python utility file."""

# pylint: disable=E0401

from flask import jsonify, request
from utils.mail import Mail


def mail() -> tuple[dict, int]:
    """
    Sends an email to the specified recipient.

    Returns:
        json: A JSON response indicating whether the email was sent successfully.
    """
    email = request.json.get("recipient")
    body = request.json.get("body")
    subject = request.json.get("subject")

    mail_instance = Mail()
    mail_instance.send_email(email, subject, body)

    return jsonify({"message": "Email sent successfully"}), 200
