# pylint: disable=E0401

import functions_framework


def is_date_later_than(start_date, end_date):
    """
    Checks if a start date is later than an end date.

    Args:
        start_date (dict): The start date.
        end_date (dict): The end date.

    Returns:
        bool: True if the start date is later than the end date, False otherwise.
    """

    return (
        (start_date["year"] > end_date["year"])
        or (
            start_date["year"] == end_date["year"]
            and start_date["month"] > end_date["month"]
        )
        or (
            start_date["year"] == end_date["year"]
            and start_date["month"] == end_date["month"]
            and start_date["day"] > end_date["day"]
        )
    )


@functions_framework.http
def ask_travel_dates(request):
    """
    Asks the user for their travel dates.

    Args:
        request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    request_json = request.get_json(silent=True)

    dates = request_json["sessionInfo"]["parameters"]["date"]
    if (len(dates)) != 2:
        res = {
            "fulfillment_response": {
                "messages": [
                    {
                        "text": {
                            "text": ["Please enter two dates for the start and end of travel"]
                        }
                    }
                ]
            },
            "targetPage": "projects/fintech-app-gcp/locations/asia-south1/agents/118233dd-f023-4dad-b302-3906a7365ccc/flows/dec04e03-aa13-48ee-8ddb-c1ffff4ddb3b/pages/2f3de251-29ed-4c8f-89b7-489f510eef8b",
            "sessionInfo": {
                "parameters": {
                    "date": None,
                }
            },
        }
        return res

    if "future" not in dates[0]:
        date1 = dates[0]
    else:
        date1 = dates[0]["future"]
    if "future" not in dates[1]:
        date2 = dates[1]
    else:
        date2 = dates[1]["future"]

    if is_date_later_than(date1, date2):
        end_date = date1
        start_date = date2
    else:
        end_date = date2
        start_date = date1

    res = {
        "fulfillment_response": {"messages": [{"text": {"text": [""]}}]},
        "sessionInfo": {
            "parameters": {
                "start_date": (
                    str(int(start_date["year"]))
                    + "-"
                    + str(int(start_date["month"]))
                    + "-"
                    + str(int(start_date["day"]))
                ),
                "end_date": (
                    str(int(end_date["year"]))
                    + "-"
                    + str(int(end_date["month"]))
                    + "-"
                    + str(int(end_date["day"]))
                ),
            }
        },
    }
    return res
