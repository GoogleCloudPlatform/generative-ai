# pylint: disable=E0401

import json
from os import environ

import functions_framework
from google.cloud import translate
import requests

project_id = environ.get("PROJECT_ID")


def detect_language(text: str) -> dict:
    """Detects the text's language."""
    from google.cloud import translate_v2 as translate

    translate_client = translate.Client()

    # Text can also be a sequence of strings, in which case this method
    # will return a sequence of results for each text.
    result = translate_client.detect_language(text)

    print(f"Text: {text}")
    print("Confidence: {}".format(result["confidence"]))
    print("Language: {}".format(result["language"]))

    return result["language"]


def post_request(url, headers, data):
    """Sends HTTP post request to URL with specified data."""
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response


def translate_fulfilment_response(
    json_data, project_id, source_language_code, destination_language_code, i=0
):
    """Translates the text of DialogFlow CX Webhook Fulfilment Response."""
    return translate_text(
        json_data["fulfillment_response"]["messages"][i]["text"]["text"][0],
        project_id,
        source_language_code,
        destination_language_code,
    )


def translate_text(
    text: str,
    project_id: str,
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

    if request_json["fulfillmentInfo"]["tag"]:
        tag = request_json["fulfillmentInfo"]["tag"]
        res_json = {}

        source_language_code = request_json["languageCode"]
        print("source language = " + source_language_code)

        """ TODO: 1. figure out the language source 2. do i need to translate
        anything in req 3. send and recive req 4. if not english, translate
        back the response (also figure out which fields need to be translated
        as such)
        """
        if tag == "rag":
            text = request_json["text"]
            if "en" in source_language_code:
                rag_qa_chain_url = environ.get("RAG_QA_CHAIN_URL")
                todo = {"query": text}
                rag_qa_chain_headers = {"Content-Type": "application/json"}
                rag_qa_chain_res = requests.post(
                    rag_qa_chain_url,
                    data=json.dumps(todo),
                    headers=rag_qa_chain_headers,
                )
                rag_qa_chain_json = rag_qa_chain_res.json()
                headers = {"Access-Control-Allow-Origin": "*"}
                return (rag_qa_chain_json, 200, headers)
            else:
                translated_text = translate_text(
                    text, project_id, source_language_code, "en-US"
                )

                rag_qa_chain_url = environ.get("RAG_QA_CHAIN_URL")
                todo = {"query": translated_text}
                rag_qa_chain_headers = {"Content-Type": "application/json"}
                rag_qa_chain_res = requests.post(
                    rag_qa_chain_url,
                    data=json.dumps(todo),
                    headers=rag_qa_chain_headers,
                )
                rag_qa_chain_json = rag_qa_chain_res.json()
                print(rag_qa_chain_json)

                response = translate_fulfilment_response(
                    rag_qa_chain_json, project_id, "en-US", source_language_code
                )

                reference_list = []

                for ref in json.loads(
                    rag_qa_chain_json["fulfillment_response"]["messages"][0]["text"][
                        "text"
                    ][1]
                ):
                    reference = {}
                    reference["matching_score"] = ref["matching_score"]
                    reference["document_source"] = ref["document_source"]
                    reference["document_name"] = translate_text(
                        ref["document_name"],
                        "fintech-app-gcp",
                        "en-US",
                        source_language_code,
                    )
                    reference["page_content"] = translate_text(
                        ref["page_content"],
                        "fintech-app-gcp",
                        "en-US",
                        source_language_code,
                    )
                    reference_list.append(reference)
                print(reference_list)
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
                # Set CORS headers for the main request
                headers = {"Access-Control-Allow-Origin": "*"}

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
            if tag == "account-summary":
                url = environ.get("ACCOUNT_SUMMARY_URL")
            elif tag == "account-tips":
                url = environ.get("ACCOUNT_TIPS_URL")
            elif tag == "event":
                url = environ.get("EVENT_RECOMM_URL")
            elif tag == "fd_confirmation":
                url = environ.get("FD_CONFIRM_URL")
            elif tag == "high-risk-mutual-fund":
                url = environ.get("HIGH_RISK_MF_URL")
            elif tag == "recommend-mutual-fund":
                url = environ.get("MF_RECOMM_URL")
            elif tag == "unusual-expense":
                url = environ.get("UNUSUAL_EXPENSE_URL")
            elif tag == "find_nearest_dealer":
                url = environ.get("FIND_NEAREST_DEALER_URL")
            elif tag == "set-default-params":
                url = environ.get("SET_DEFAULT_PARAM_URL")

            res = post_request(
                url=url, data=request_json, headers={"Content-Type": "application/json"}
            )
            res_json = res.json()
            headers = {"Access-Control-Allow-Origin": "*"}

            if "en" not in source_language_code:
                res_json["fulfillment_response"]["messages"][0]["text"]["text"][
                    0
                ] = translate_fulfilment_response(
                    res_json, project_id, "en-US", source_language_code
                )

        elif tag in [
            "account-balance",
            "credit-card-recommendation",
            "create-credit-card",
            "fd-recommendation",
            "fd_tenure",
            "create-fd",
        ]:
            if tag == "account-balance":
                url = environ.get("ACCOUNT_BALANCE_URL")
            elif tag == "credit-card-recommendation":
                url = environ.get("CREDIT_CARD_RECOMM_URL")
            elif tag == "create-credit-card":
                url = environ.get("CREDIT_CARD_CREATE_URL")
            elif tag == "fd-recommendation":
                url = environ.get("FD_RECOMM_URL")
            elif tag == "fd_tenure":
                url = environ.get("FD_TENURE_URL")
            elif tag == "create-fd":
                url = environ.get("FD_CREATE_URL")

            res = post_request(
                url=url, data=request_json, headers={"Content-Type": "application/json"}
            )
            print(res)
            res_json = res.json()
            headers = {"Access-Control-Allow-Origin": "*"}

            if "en" not in source_language_code:
                for i in range(len(res_json["fulfillment_response"]["messages"])):
                    res_json["fulfillment_response"]["messages"][i]["text"]["text"][
                        0
                    ] = translate_fulfilment_response(
                        res_json, project_id, "en-US", source_language_code, i
                    )

        elif tag == "category-wise-expenditure":
            url = environ.get("CATEGORIZE_EXPENSE_URL")
            res = post_request(
                url=url, data=request_json, headers={"Content-Type": "application/json"}
            )
            res_json = res.json()
            headers = {"Access-Control-Allow-Origin": "*"}
            if "en" not in source_language_code:
                res_json["fulfillment_response"]["messages"][0]["text"]["text"][
                    0
                ] = translate_fulfilment_response(
                    res_json, project_id, "en-US", source_language_code
                )
                for i in range(
                    len(
                        res_json["fulfillment_response"]["messages"][1]["payload"][
                            "richContent"
                        ][0][0]["text"]
                    )
                ):
                    res_json["fulfillment_response"]["messages"][1]["payload"][
                        "richContent"
                    ][0][0]["text"][i] = translate_text(
                        res_json["fulfillment_response"]["messages"][1]["payload"][
                            "richContent"
                        ][0][0]["text"][i],
                        project_id,
                        "en-US",
                        source_language_code,
                    )

        elif tag in [
            "debt_fund_webhook",
            "expense-prediction",
            "recommend-debt-fund",
            "travel",
        ]:
            if tag == "debt_fund_webhook":
                url = environ.get("DEBT_FUND_URL")
            elif tag == "expense-prediction":
                url = environ.get("EXPENSE_PREDICT_URL")
            elif tag == "recommend-debt-fund":
                url = environ.get("DEBT_FUND_RECOMM_URL")
            elif tag == "travel":
                url = environ.get("TRAVEL_EVENT_RECOMM_URL")

            res = post_request(
                url=url, data=request_json, headers={"Content-Type": "application/json"}
            )
            res_json = res.json()
            headers = {"Access-Control-Allow-Origin": "*"}
            if "en" not in source_language_code:
                for i in range(len(res_json["fulfillment_response"]["messages"])):
                    if "text" in res_json["fulfillment_response"]["messages"][i]:
                        res_json["fulfillment_response"]["messages"][i]["text"]["text"][
                            0
                        ] = translate_text(
                            res_json["fulfillment_response"]["messages"][i]["text"][
                                "text"
                            ][0],
                            project_id,
                            "en-US",
                            source_language_code,
                        )

        elif tag == "tenure-validation":
            url = environ.get("FD_TENURE_VAL_URL")
            request_json["sessionInfo"]["parameters"]["fd_tenure"] = translate_text(
                request_json["sessionInfo"]["parameters"]["fd_tenure"],
                project_id,
                source_language_code,
                "en-US",
            )
            res = post_request(
                url=url, data=request_json, headers={"Content-Type": "application/json"}
            )
            res_json = res.json()
            headers = {"Access-Control-Allow-Origin": "*"}

        return (res_json, 200, headers)

    # [end] handle translation for chatbot webhooks#

    # [start] code will handle translation for searcg queries from the website

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

    if request_json and "query" in request_json:
        text = request_json["query"]
    else:
        text = "म्यूचुअल फंड क्या होता है?"
    source_language_code = detect_language(text)

    rag_qa_chain_url = environ.get("RAG_QA_CHAIN_URL")

    if "en" in source_language_code:
        data = {"query": text}
        rag_qa_chain_res = post_request(
            url=rag_qa_chain_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        rag_qa_chain_json = rag_qa_chain_res.json()
        headers = {"Access-Control-Allow-Origin": "*"}
        return (rag_qa_chain_json, 200, headers)

    translated_text = translate_text(text, project_id, source_language_code, "en-US")

    data = {"query": translated_text}
    rag_qa_chain_res = post_request(
        url=rag_qa_chain_url, data=data, headers={"Content-Type": "application/json"}
    )
    rag_qa_chain_json = rag_qa_chain_res.json()
    print(rag_qa_chain_json)

    response = translate_text(
        rag_qa_chain_json["fulfillment_response"]["messages"][0]["text"]["text"][0],
        "fintech-app-gcp",
        "en-US",
        source_language_code,
    )
    reference_list = []

    for ref in json.loads(
        rag_qa_chain_json["fulfillment_response"]["messages"][0]["text"]["text"][1]
    ):
        reference = {}
        print(ref)
        print(type(ref))
        reference["matching_score"] = ref["matching_score"]
        reference["document_source"] = ref["document_source"]
        reference["document_name"] = translate_text(
            ref["document_name"],
            "fintech-app-gcp",
            "en-US",
            source_language_code,
        )
        reference["page_content"] = translate_text(
            ref["page_content"],
            "fintech-app-gcp",
            "en-US",
            source_language_code,
        )
        reference_list.append(reference)
    print(reference_list)
    res_json = {
        "fulfillment_response": {
            "messages": [{"text": {"text": [response, json.dumps(reference_list)]}}]
        }
    }
    # Set CORS headers for the main request
    headers = {"Access-Control-Allow-Origin": "*"}
    return (res_json, 200, headers)

    # [end] code will handle translation for es queries from the website
