"""This is a python utility file."""

# pylint: disable=E0401

config = {
    "PROJECT_ID": "<PROJECT_ID>",
    "LOCATION": "<LOCATION>",
    "gemini_parameters": {
        "max_output_tokens": 1024,
        "temperature": 0.05,
        "top_p": 0.7,
        "top_k": 20,
    },
    "MIME_TYPE_PDF": "application/pdf",
    "MIME_TYPE_PNG": "image/png",
    "text_bison_parameters": {
        "max_output_tokens": 2048,
        "temperature": 0.05,
        "top_p": 0.8,
        "top_k": 40,
    },
    "company_email": "<COMPANY_EMAIL>",
    "mail_password": "<MAIL_PASSWORD>",
    "CALENDAR_SCOPE": "https://www.googleapis.com/auth/calendar",
    "EMAIL_SCOPE": "https://www.googleapis.com/auth/script.projects",
    "MAIL_TRIAL_SCOPE": "https://mail.google.com/",
    "text_bison_model": "text-bison-32k",
    "gemini_model": "gemini-pro",
}
