import functions_framework


def is_date_later_than(start_date, end_date):
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
def hello_http(request):

    request_json = request.get_json(silent=True)

    print(request_json["sessionInfo"]["parameters"])

    dates = request_json["sessionInfo"]["parameters"]["date"]
    if (len(dates)) != 2:
        res = {
            "fulfillment_response": {
                "messages": [
                    {
                        "text": {
                            "text": [
                                "Please enter two dates for the start and end of"
                                " travel"
                            ]
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
        print(res)
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

    print(start_date)
    print(end_date)

    res = {
        "fulfillment_response": {"messages": [{"text": {"text": [""]}}]},
        # "targetPage": "/projects/fintech-app-gcp/locations/us-central1/agents/ba85d3e8-3197-4938-baec-5f6dd65e7320/flows/00000000-0000-0000-0000-000000000000/pages/Get_Date",
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
    print(res)
    return res
