"""This is a python utility file."""

# pylint: disable=E0401

import datetime
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
import imaplib
import os
from os.path import basename
import smtplib
from typing import Any

from config import config
import markdown


class Mail:
    """
    Class to send and receive emails.
    """

    def __init__(
        self, sender=config["company_email"], password=config["mail_password"]
    ):
        """
        Initializes the Mail class.

        Args:
            sender (str): The email address of the sender.
            password (str): The password of the sender.
        """
        self.sender = sender
        self.password = password

    def send_email(self, to_mail, subject, body, file_path: Any = None) -> None:
        """
        Sends an email.

        Args:
            to_mail (str): The email address of the recipient.
            subject (str): The subject of the email.
            body (str): The body of the email.
            file_path (str): The path to a file to attach to the email
        """
        try:
            body = markdown.markdown(body)
            msg = MIMEMultipart()
            msg["From"] = self.sender
            msg["To"] = to_mail
            msg["Date"] = formatdate(localtime=True)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))

            if file_path is not None:
                with open(file_path, "rb") as fil:
                    part = MIMEApplication(fil.read(), Name=basename(file_path))
                # After the file is closed
                content_dis = f'attachment; filename="{basename(file_path)}"'
                part["Content-Disposition"] = content_dis
                msg.attach(part)

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(self.sender, self.password)
            server.sendmail(self.sender, to_mail, msg.as_string())
            server.quit()
            print("Email sent successfully")

        except ValueError as e:
            print("Error: unable to send email", e)

    # pylint: disable=R0914
    def send_calendar_event(self, param: dict) -> None:
        """
        Function to send an ics file of the event to the email account of the receipient

            INPUT: param (dict):
                -receiver (list):  mail ids of receiver
                -start_date (dateTime): start date of the event
                -end_date (dateTime): end date of the event
                -location (str): meet link
                -subject (str): subject of the event

        """

        try:
            param["location"]
        except ValueError as e:
            print(e)
            param["location"] = "https://meet.google.com/ybf-xwfa-ygj"

        crlf = "\r\n"
        attendees = ""
        try:
            for att in param["receiver"]:
                attendees += (
                    "ATTENDEE;CUTYPE=INDIVIDUAL;\
                        ROLE=REQ-PARTICIPANT;\
                        PARTSTAT=NEEDS-ACTION;RSVP=FALSE;CN="
                    + att
                    + ";X-NUM-GUESTS=0:mailto:"
                    + att
                    + crlf
                )
        except ValueError as e:
            print(e)

        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        f = os.path.join(__location__, "invite.ics")

        with open(f, encoding="UTF-8") as file:
            ics_content = file.read()

        replaced_contents = ics_content.replace(
            "start_date", param["start_date"].strftime("%Y%m%dT%H%M%SZ")
        )
        try:
            replaced_contents = replaced_contents.replace(
                "end_date", param["end_date"].strftime("%Y%m%dT%H%M%SZ")
            )
            replaced_contents = replaced_contents.replace(
                "telephonic", param["location"]
            )
            replaced_contents = replaced_contents.replace(
                "now", datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")
            )
        except ValueError as e:
            print(e)

        replaced_contents = replaced_contents.replace("attend", attendees)
        replaced_contents = replaced_contents.replace("subject", param["subject"])
        replaced_contents = replaced_contents.replace("describe", param["subject"])

        part_email = MIMEText(replaced_contents, "calendar;method=REQUEST")
        ical_atch = MIMEBase("text/calendar", ' ;name="invitation.ics"')
        ical_atch.set_payload(replaced_contents)
        ical_atch.add_header("Content-Disposition", f'attachment; filename="{f}"')

        msg_alternative = MIMEMultipart("alternative")
        msg_alternative.attach(part_email)
        msg = MIMEMultipart("mixed")
        msg["Reply-To"] = self.sender
        msg["Date"] = formatdate(localtime=True)
        msg["Subject"] = param["subject"]
        msg["From"] = self.sender
        msg["To"] = param["receiver"]
        msg.attach(msg_alternative)
        mail_server = smtplib.SMTP("smtp.gmail.com", 587)
        mail_server.ehlo()
        mail_server.starttls()
        mail_server.ehlo()
        mail_server.login(self.sender, self.password)
        mail_server.sendmail(self.sender, param["receiver"], msg.as_string())
        mail_server.close()

        print("Email sent successfully")

    # pylint: disable=R0914
    def read_email(self):
        """
        Reads emails from the inbox.
        """
        user = config["company_email"]
        password = config["mail_password"]
        imap_url = "imap.gmail.com"

        # Function to get email content part i.e its body part
        def get_body(msg):
            if msg.is_multipart():
                return get_body(msg.get_payload(0))
            return msg.get_payload(None, True)

        # Function to search for a key value pair
        def search(key, value, con):
            _, data = con.search(None, key, f'"{value}"')
            return data

        # Function to get the list of emails under this label
        def get_emails(result_bytes):
            msgs = []  # all the email data are pushed inside an array
            for num in result_bytes[0].split():
                _, data = con.fetch(num, "(RFC822)")
                msgs.append(data)

            return msgs

        # this is done to make SSL connection with GMAIL
        con = imaplib.IMAP4_SSL(imap_url)

        # logging the user in
        con.login(user, password)

        # calling function to check for email under this label
        con.select("Inbox")

        msgs = get_emails(search("FROM", "*", con))

        print("Messages: ", msgs)
        for msg in msgs[::-1]:
            for sent in msg:
                if isinstance(sent, tuple):
                    content = str(sent[1], "utf-8")
                    data = str(content)

                    try:
                        indexstart = data.find("ltr")
                        # pylint: disable=C2801
                        data2 = data.__getitem__(slice(indexstart + 5, len(data)))
                        indexend = data2.find("</div>")
                        print(data2[0:indexend])

                    except UnicodeEncodeError as e:
                        print(e)
