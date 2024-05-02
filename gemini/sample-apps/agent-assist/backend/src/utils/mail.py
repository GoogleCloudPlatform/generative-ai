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
import markdown # type: ignore


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

    def send_email(self, to_mail, subject, body, filepath: Any = None) -> None:
        """
        Sends an email.

        Args:
            to_mail (str): The email address of the recipient.
            subject (str): The subject of the email.
            body (str): The body of the email.
            filepath (str): The path to a file to attach to the email
        """
        try:
            body = markdown.markdown(body)
            msg = MIMEMultipart()
            msg["From"] = self.sender
            msg["To"] = to_mail
            msg["Date"] = formatdate(localtime=True)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))

            if filepath is not None:
                with open(filepath, "rb") as fil:
                    part = MIMEApplication(fil.read(), Name=basename(filepath))
                # After the file is closed
                part["Content-Disposition"] = 'attachment; filename="%s"' % basename(
                    filepath
                )
                msg.attach(part)

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(self.sender, self.password)
            server.sendmail(self.sender, to_mail, msg.as_string())
            server.quit()
            print("Email sent successfully")

        except Exception as e:
            print("Error: unable to send email", e)

    def send_calendar_event(self, param: dict) -> None:
        """
        Function to send an ics file of the event to the email account of the receipient

            INPUT: param (dict):
                -receiver (list):  mail ids of receiver
                -startDate (dateTime): start date of the event
                -endDate (dateTime): end date of the event
                -location (str): meet link
                -subject (str): subject of the event

        """

        try:
            param["location"]
        except Exception as e:
            print(e)
            param["location"] = "https://meet.google.com/ybf-xwfa-ygj"

        CRLF = "\r\n"
        attendees = ""
        try:
            for att in param["receiver"]:
                attendees += (
                    "ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=FALSE;CN="
                    + att
                    + ";X-NUM-GUESTS=0:mailto:"
                    + att
                    + CRLF
                )
        except Exception as e:
            print(e)

        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        f = os.path.join(__location__, "invite.ics")
        ics_content = open(f).read()

        replaced_contents = ics_content.replace(
            "startDate", param["startDate"].strftime("%Y%m%dT%H%M%SZ")
        )
        try:
            replaced_contents = replaced_contents.replace(
                "endDate", param["endDate"].strftime("%Y%m%dT%H%M%SZ")
            )
            replaced_contents = replaced_contents.replace(
                "telephonic", param["location"]
            )
            replaced_contents = replaced_contents.replace(
                "now", datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")
            )
        except Exception as e:
            print(e)

        replaced_contents = replaced_contents.replace("attend", attendees)
        replaced_contents = replaced_contents.replace("subject", param["subject"])
        replaced_contents = replaced_contents.replace("describe", param["subject"])

        part_email = MIMEText(replaced_contents, "calendar;method=REQUEST")
        ical_atch = MIMEBase("text/calendar", ' ;name="%s"' % "invitation.ics")
        ical_atch.set_payload(replaced_contents)
        ical_atch.add_header("Content-Disposition", 'attachment; filename="%s"' % f)

        msgAlternative = MIMEMultipart("alternative")
        msgAlternative.attach(part_email)
        msg = MIMEMultipart("mixed")
        msg["Reply-To"] = self.sender
        msg["Date"] = formatdate(localtime=True)
        msg["Subject"] = param["subject"]
        msg["From"] = self.sender
        msg["To"] = param["receiver"]
        msg.attach(msgAlternative)
        mailServer = smtplib.SMTP("smtp.gmail.com", 587)
        mailServer.ehlo()
        mailServer.starttls()
        mailServer.ehlo()
        mailServer.login(self.sender, self.password)
        mailServer.sendmail(self.sender, param["receiver"], msg.as_string())
        mailServer.close()

        print("Email sent successfully")

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
            else:
                return msg.get_payload(None, True)

        # Function to search for a key value pair
        def search(key, value, con):
            result, data = con.search(None, key, '"{}"'.format(value))
            return data

        # Function to get the list of emails under this label
        def get_emails(result_bytes):
            msgs = []  # all the email data are pushed inside an array
            for num in result_bytes[0].split():
                typ, data = con.fetch(num, "(RFC822)")
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
                if type(sent) is tuple:
                    content = str(sent[1], "utf-8")
                    data = str(content)

                    try:
                        indexstart = data.find("ltr")
                        data2 = data.__getitem__(slice(indexstart + 5, len(data)))
                        indexend = data2.find("</div>")
                        print(data2[0:indexend])

                    except UnicodeEncodeError as e:
                        print(e)
