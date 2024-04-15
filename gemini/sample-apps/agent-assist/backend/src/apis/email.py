from flask import jsonify, request

from utils.mail import Mail


def mail():
    """
    Sends an email to the specified recipient.

    Args:
        email (str): The email address of the recipient.
        body (str):
        The body of the email.
        subject (str): The subject of the email.

    Returns:
        json: A JSON response indicating whether the email was sent
        successfully.

    """
    email = request.json.get("recipient")
    body = request.json.get("body")
    subject = request.json.get("subject")

    mail = Mail()
    mail.send_email(email, subject, body)

    return jsonify({"message": "Email sent successfully"}), 200
