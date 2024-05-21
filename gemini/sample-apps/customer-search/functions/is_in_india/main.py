"""This is a python utility file."""

# pylint: disable=E0401
# pylint: disable=R0801
# pylint: disable=R0914

from os import environ

import functions_framework
import requests

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def check_is_city_in_india(request):
    """
    Checks if a given city is in India.

    Args:
        request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    places_api_key = environ.get("MAPS_API_KEY")
    request_json = request.get_json(silent=True)

    city = None
    country = None

    for place in request_json["sessionInfo"]["parameters"]["destination"]:
        if "city" in place:
            city = place["city"]
        if "country" in place:
            country = place["country"]

    if city is None and country is None:
        res = {
            "fulfillment_response": {
                "messages": [
                    {
                        "text": {
                            "text": [
                                "Please enter the city or country you are travelling to"
                            ]
                        }
                    }
                ]
            },
            "targetPage": """/projects/fintech-app-gcp/locations/us-central1/agents/\
            ba85d3e8-3197-4938-baec-5f6dd65e7320/flows/00000000-0000-0000-0000-000000000000/\
            pages/Get_Destination""",
        }
        return res

    # 1. get the place id
    # 2. get the country from the place id
    # 3. store it in a session variable

    if country is None:
        get_place_id_url = f"""https://maps.googleapis.com/maps/api/place/findplacefromtext/\
        json?input={city}&inputtype=textquery&key={places_api_key}"""
        headers = {"Content-Type": "application/json"}
        place_id_res = requests.get(get_place_id_url, headers=headers)
        place_id_json = place_id_res.json()

        place_id = place_id_json["candidates"][0]["place_id"]

        get_place_details_url = f"""https://maps.googleapis.com/maps/api/place/details/\
        json?place_id={place_id}&key={places_api_key}"""
        headers = {"Content-Type": "application/json"}
        place_details_res = requests.get(get_place_details_url, headers=headers)
        place_details_json = place_details_res.json()
        for place in place_details_json["result"]["address_components"]:
            if "country" in place["types"]:
                country = place["long_name"]

    if city is not None:
        res = {
            "sessionInfo": {
                "parameters": {
                    "city": city,
                    "country": country,
                }
            }
        }
    else:
        res = {
            "sessionInfo": {
                "parameters": {
                    "country": country,
                }
            }
        }
    return res
