"""This is a python utility file created for help."""

# pylint: disable=E0401

from datetime import datetime

from flask import jsonify
from utils.cal import Calendar


def get_calendar_events() -> tuple[jsonify, int]:
    """Gets a list of events for today's date and
    returns them as a JSON response with a status code of 200.

    Returns:
        tuple[jsonify, int]: A tuple containing the JSON response and the status code.
    """
    calendar = Calendar()

    today_date = datetime.now().strftime("%d/%m/%Y")
    events = calendar.get_events_by_date(today_date)
    return jsonify(events), 200
