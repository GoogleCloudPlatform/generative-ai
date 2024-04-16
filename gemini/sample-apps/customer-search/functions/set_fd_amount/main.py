import functions_framework


@functions_framework.http
def hello_http(request):
    request_json = request.get_json(silent=True)

    print(request_json)

    fd_amount = request_json["sessionInfo"]["parameters"]["number"]

    res = {
        "fulfillment_response": {"messages": [{"text": {"text": []}}]},
        "sessionInfo": {
            "parameters": {
                "fd_amount": fd_amount,
            }
        },
    }
    print(res)
    return res
