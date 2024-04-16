import functions_framework


@functions_framework.http
def hello_http(request):
    request_json = request.get_json(silent=True)

    destination = request_json["sessionInfo"]["parameters"]["Destination"]

    res = {
        "fulfillment_response": {"messages": [{"text": {"text": []}}]},
        "sessionInfo": {
            "parameters": {
                "Destination": destination,
            }
        },
    }
    print(res)
    return res
