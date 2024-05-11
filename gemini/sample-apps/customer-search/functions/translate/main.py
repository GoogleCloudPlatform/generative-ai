# pylint: disable=E0401

import json
from os import environ

import functions_framework
from google.cloud import translate
import requests

# Define the project ID as an environment variable
project_id = environ.get("PROJECT_ID")


def detect_language(text: str) -> dict:
    """Detects the text's language.

    Args:
        text (str): The text to detect the language of.

    Returns:
        dict: A dictionary containing the detected language and its confidence.
    """
    from google.cloud import translate_v2 as translate

    translate_client = translate.Client()

    # Text can also be a sequence of strings, in which case this method
    # will return a sequence of results for each text.
    result = translate_client.detect_language(text)

    print(f"Text: {text}")
    print("Confidence: {}".format(result["confidence"]))
    print("Language: {}".format(result["language"]))

    return result["language"]


# Initialize Translation client


def translate_text(
    text: str,
    project_id: str,
    source_language_code: str,
    target_language_code: str,
) -> translate.TranslationServiceClient:
    """Translating Text.

    Args:
        text (str): The text to translate.
        project_id (str): The project ID of the Google Cloud project you want to use.
        source_language_code (str): The language code of the source text.
        target_language_code (str): The language code of the target text.

    Returns:
        translate.TranslationServiceClient: The translated text.
    """

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

    print(response.translations[0])
    print(type(response.translations[0]))
    return response.translations[0].translated_text


@functions_framework.http
def translate(request):
    """
    Translates text from one language to another.

    Args:
        request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    request_json = request.get_json(silent=True)

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

    translated_text = translate_text(text, project_id, source_language_code, "en-US")

    rag_qa_chain_url = environ.get("RAG_QA_CHAIN_URL")
    todo = {"query": translated_text}
    rag_qa_chain_headers = {"Content-Type": "application/json"}
    rag_qa_chain_res = requests.post(
        rag_qa_chain_url, data=json.dumps(todo), headers=rag_qa_chain_headers
    )
    rag_qa_chain_json = rag_qa_chain_res.json()
    print(rag_qa_chain_json)

    response = translate_text(
        rag_qa_chain_json["fulfillment_response"]["messages"][0]["text"]["text"][0],
        project_id,
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
            ref["document_name"], project_id, "en-US", source_language_code
        )
        reference["page_content"] = translate_text(
            ref["page_content"], project_id, "en-US", source_language_code
        )
        reference_list.append(reference)
    print(reference_list)
    res = {
        "fulfillment_response": {
            "messages": [{"text": {"text": [response, json.dumps(reference_list)]}}]
        }
    }
    # Set CORS headers for the main request
    headers = {"Access-Control-Allow-Origin": "*"}
    return (res, 200, headers)
