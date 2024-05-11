# pylint: disable=E0401

import functions_framework


@functions_framework.http
def set_fd_amount(request):
    """
    Sets the fixed deposit amount for a customer.

    Args:
        request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

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
