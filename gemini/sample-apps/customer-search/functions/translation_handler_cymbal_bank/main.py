"""This is a python utility file."""

# pylint: disable=E0401
# pylint: disable=R0801

import json
from os import environ

import functions_framework
from google.cloud import translate_v2 as translate
import requests

project_id = environ.get("PROJECT_ID")


def detect_language(text: str) -> dict:
    """Detects the text's language."""

    translate_client = translate.Client()

    # Text can also be a sequence of strings, in which case this method
    # will return a sequence of results for each text.
    result = translate_client.detect_language(text)

    print(f"Text: {text}")
    print(f"Confidence: {result['confidence']}")
    print(f"Language: {result['language']}")

    return result["language"]


def post_request(url, headers, data):
    """Sends HTTP post request to URL with specified data."""
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response


def translate_fulfilment_response(
    json_data, source_language_code, destination_language_code, i=0
):
    """Translates the text of DialogFlow CX Webhook Fulfilment Response."""
    return translate_text(
        json_data["fulfillment_response"]["messages"][i]["text"]["text"][0],
        source_language_code,
        destination_language_code,
    )


def translate_text(
    text: str,
    source_language_code: str,
    target_language_code: str,
) -> translate.TranslationServiceClient:
    """Translating Text."""

    client = translate.TranslationServiceClient()

    location = "global"

    parent = f"projects/{project_id}/locations/{location}"

    # Translate text from English to French
    # Detail on supported types can be found here:
    # https://cloud.google.com/translate/docs/supported-formats
    response = client.translate_text(
        request={
            "parent": parent,
            "contents": [text],
            "mime_type": "text/plain",  # mime types: text/plain, text/html
            "source_language_code": source_language_code,
            "target_language_code": target_language_code,
        }
    )

    # Display the translation for each input text provided
    for translation in response.translations:
        print(f"Translated text: {translation.translated_text}")

    return response.translations[0].translated_text


def handle_rag_webhook(
    text: str, source_language_code: str, request_headers: dict
) -> dict:
    """Handles translation for rag webhook from the website."""

    rag_qa_chain_url = environ.get("RAG_QA_CHAIN_URL")
    if "en" in source_language_code:
        todo = {"query": text}
        return get_json_response(rag_qa_chain_url, todo, request_headers)

    translated_text = translate_text(text, source_language_code, "en-US")

    todo = {"query": translated_text}

    rag_qa_chain_json = get_json_response(rag_qa_chain_url, todo, request_headers)
    response = translate_fulfilment_response(
        rag_qa_chain_json, "en-US", source_language_code
    )

    reference_list = []

    for ref in json.loads(
        rag_qa_chain_json["fulfillment_response"]["messages"][0]["text"]["text"][1]
    ):
        reference = {}
        reference["matching_score"] = ref["matching_score"]
        reference["document_source"] = ref["document_source"]
        reference["document_name"] = translate_text(
            ref["document_name"],
            "en-US",
            source_language_code,
        )
        reference["page_content"] = translate_text(
            ref["page_content"],
            "en-US",
            source_language_code,
        )
        reference_list.append(reference)

    res_json = {
        "fulfillment_response": {
            "messages": [
                {
                    "text": {
                        "text": [
                            response,
                            json.dumps(reference_list),
                        ]
                    }
                }
            ]
        }
    }
    return res_json


def handle_category_wise_expenditure_webhook(
    request_json: dict, request_headers: dict, source_language_code: str
) -> dict:
    """Handles translation for category wise expenditure webhook from the website."""

    url = environ.get("CATEGORIZE_EXPENSE_URL")
    res_json = get_json_response(url, request_json, request_headers)
    if "en" not in source_language_code:
        res_json["fulfillment_response"]["messages"][0]["text"]["text"][0] = (
            translate_fulfilment_response(res_json, "en-US", source_language_code)
        )
        for i in range(
            len(
                res_json["fulfillment_response"]["messages"][1]["payload"][
                    "richContent"
                ][0][0]["text"]
            )
        ):
            res_json["fulfillment_response"]["messages"][1]["payload"]["richContent"][
                0
            ][0]["text"][i] = translate_text(
                res_json["fulfillment_response"]["messages"][1]["payload"][
                    "richContent"
                ][0][0]["text"][i],
                "en-US",
                source_language_code,
            )
    return res_json


def handle_webhook(request_json: dict) -> dict:
    """
    Handles translation for chatbot webhooks from the website.

    Args:
        request_json (dict): The request JSON containing the webhook information.

    Returns:
        dict: The translated response JSON.
    """

    tag = request_json["fulfillmentInfo"]["tag"]
    res_json = {}

    source_language_code = request_json["languageCode"]

    request_headers = {"Content-Type": "application/json"}

    # 1. figure out the language source
    # 2. do i need to translate anything in req
    # 3. send and recive req
    # 4. if not english, translate back the response (also figure out which
    # fields need to be translated as such)
    if tag == "rag":
        text = request_json["text"]
        res_json = handle_rag_webhook(text, source_language_code, request_headers)

    elif tag in [
        "set-default-params",
        "account-summary",
        "account-tips",
        "event",
        "fd_confirmation",
        "high-risk-mutual-fund",
        "recommend-mutual-fund",
        "unusual-expense",
        "find_nearest_dealer",
    ]:
        url = {
            "account-summary": environ.get("ACCOUNT_SUMMARY_URL"),
            "account-tips": environ.get("ACCOUNT_TIPS_URL"),
            "event": environ.get("EVENT_RECOMM_URL"),
            "fd_confirmation": environ.get("FD_CONFIRM_URL"),
            "high-risk-mutual-fund": environ.get("HIGH_RISK_MF_URL"),
            "recommend-mutual-fund": environ.get("MF_RECOMM_URL"),
            "unusual-expense": environ.get("UNUSUAL_EXPENSE_URL"),
            "find_nearest_dealer": environ.get("FIND_NEAREST_DEALER_URL"),
            "set-default-params": environ.get("SET_DEFAULT_PARAM_URL"),
        }.get(tag)

        res_json = get_json_response(url, request_json, request_headers)

        if "en" not in source_language_code:
            res_json["fulfillment_response"]["messages"][0]["text"]["text"][0] = (
                translate_fulfilment_response(res_json, "en-US", source_language_code)
            )

    elif tag in [
        "account-balance",
        "credit-card-recommendation",
        "create-credit-card",
        "fd-recommendation",
        "fd_tenure",
        "create-fd",
    ]:
        url = {
            "account-balance": environ.get("ACCOUNT_BALANCE_URL"),
            "credit-card-recommendation": environ.get("CREDIT_CARD_RECOMM_URL"),
            "create-credit-card": environ.get("CREDIT_CARD_CREATE_URL"),
            "fd-recommendation": environ.get("FD_RECOMM_URL"),
            "fd_tenure": environ.get("FD_TENURE_URL"),
            "create-fd": environ.get("FD_CREATE_URL"),
        }.get(tag)

        res_json = get_json_response(url, request_json, request_headers)

        if "en" not in source_language_code:
            for i in range(len(res_json["fulfillment_response"]["messages"])):
                res_json["fulfillment_response"]["messages"][i]["text"]["text"][0] = (
                    translate_fulfilment_response(
                        res_json, "en-US", source_language_code, i
                    )
                )

    elif tag == "category-wise-expenditure":
        res_json = handle_category_wise_expenditure_webhook(
            request_json, request_headers, source_language_code
        )

    elif tag in [
        "debt_fund_webhook",
        "expense-prediction",
        "recommend-debt-fund",
        "travel",
    ]:
        url = {
            "debt_fund_webhook": environ.get("DEBT_FUND_URL"),
            "expense-prediction": environ.get("EXPENSE_PREDICT_URL"),
            "recommend-debt-fund": environ.get("DEBT_FUND_RECOMM_URL"),
            "travel": environ.get("TRAVEL_EVENT_RECOMM_URL"),
        }.get(tag)

        res_json = get_json_response(url, request_json, request_headers)
        if "en" not in source_language_code:
            for i in range(len(res_json["fulfillment_response"]["messages"])):
                if "text" in res_json["fulfillment_response"]["messages"][i]:
                    res_json["fulfillment_response"]["messages"][i]["text"]["text"][
                        0
                    ] = translate_text(
                        res_json["fulfillment_response"]["messages"][i]["text"]["text"][
                            0
                        ],
                        "en-US",
                        source_language_code,
                    )

    elif tag == "tenure-validation":
        url = environ.get("FD_TENURE_VAL_URL")
        request_json["sessionInfo"]["parameters"]["fd_tenure"] = translate_text(
            request_json["sessionInfo"]["parameters"]["fd_tenure"],
            source_language_code,
            "en-US",
        )
        res_json = get_json_response(url, request_json, request_headers)

    return res_json


def handle_search(request_json):
    """
    Handles translation for search results from the website.

    Args:
        request_json (dict): The request JSON containing the webhook information.

    Returns:
        dict: The translated response JSON.
    """

    if request_json and "query" in request_json:
        text = request_json["query"]
    else:
        text = "म्यूचुअल फंड क्या होता है?"

    source_language_code = detect_language(text)

    rag_qa_chain_url = environ.get("RAG_QA_CHAIN_URL")

    request_headers = {"Content-Type": "application/json"}

    if "en" in source_language_code:
        data = {"query": text}
        return get_json_response(rag_qa_chain_url, data, request_headers)

    translated_text = translate_text(text, source_language_code, "en-US")

    data = {"query": translated_text}
    rag_qa_chain_json = get_json_response(rag_qa_chain_url, data, request_headers)

    response = translate_text(
        rag_qa_chain_json["fulfillment_response"]["messages"][0]["text"]["text"][0],
        "en-US",
        source_language_code,
    )
    reference_list = []

    for ref in json.loads(
        rag_qa_chain_json["fulfillment_response"]["messages"][0]["text"]["text"][1]
    ):
        reference = {}
        reference["matching_score"] = ref["matching_score"]
        reference["document_source"] = ref["document_source"]
        reference["document_name"] = translate_text(
            ref["document_name"],
            "en-US",
            source_language_code,
        )
        reference["page_content"] = translate_text(
            ref["page_content"],
            "en-US",
            source_language_code,
        )
        reference_list.append(reference)

    res_json = {
        "fulfillment_response": {
            "messages": [{"text": {"text": [response, json.dumps(reference_list)]}}]
        }
    }

    return res_json


def get_json_response(url: str, data: dict, headers: dict) -> dict:
    """
    Sends a POST request to the specified URL with the provided data and headers,
    and returns the JSON response.

    Args:
        url (str): The URL to send the request to.
        data (dict): The data to send in the request body.
        headers (dict): The headers to send in the request.

    Returns:
        dict: The JSON response from the server.
    """

    rag_qa_chain_res = requests.post(
        url,
        data=data,
        headers=headers,
    )
    return rag_qa_chain_res.json()


@functions_framework.http
def translation_handler(request):
    """
    Handles translation for chatbot webhooks and search queries from the website.

    Args:
        request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    request_json = request.get_json(silent=True)

    headers = {"Access-Control-Allow-Origin": "*"}

    if request_json["fulfillmentInfo"]["tag"]:
        return (handle_webhook(request_json), 200, headers)

    if request.method == "OPTIONS":
        # Allows GET requests from any origin with the Content-Type
        # header and caches preflight response for an 3600s
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }

        return ("", 204, headers)

    return (handle_search(request_json), 200, headers)
