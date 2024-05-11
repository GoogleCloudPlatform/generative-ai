# pylint: disable=E0401

import json
import os
from os import environ
import textwrap
import urllib.request

import functions_framework
from langchain.chains import RetrievalQA
from langchain.document_loaders import WebBaseLoader
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_vertexai import (
    VectorSearchVectorStore,
    VertexAI,
    VertexAIEmbeddings,
)
import nest_asyncio
import vertexai
from vertexai.language_models import TextGenerationModel

project_id = environ.get("PROJECT_ID")


def init_me_libs():
    """
    Initializes the necessary libraries for the module.
    """

    if not os.path.exists("utils"):
        os.makedirs("utils")

    url_prefix = "https://raw.githubusercontent.com/GoogleCloudPlatform/generative-ai/main/language/use-cases/document-qa/utils"
    files = ["__init__.py", "matching_engine.py", "matching_engine_utils.py"]

    for fname in files:
        urllib.request.urlretrieve(f"{url_prefix}/{fname}", filename=f"utils/{fname}")


init_me_libs()


def load_website_content():
    """
    Loads the content of the website.

    Returns:
        A list of documents.
    """

    nest_asyncio.apply()

    loader = WebBaseLoader(
        [
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/upi",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/imps",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/neft",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/credit_card",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/recharge",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/electricity",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/insurance_premium",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/saving/terms_and_condition",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/saving",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/current",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/salary",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/fixed_deposit",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/recurring_deposit",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/stocks",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/ipo",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/mutual_funds",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/loans",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/loans/terms_and_condition",
            "https://cymbal-bank-web-deployed-n3zk63yvta-uc.a.run.app/loans/agreement",
        ]
    )
    loader.requests_per_second = 1

    documents = loader.aload()
    return documents


def chunk_documents(documents):
    """
    Chunks the documents into smaller chunks.

    Args:
        documents (list): The list of documents to chunk.

    Returns:
        A list of document chunks.
    """

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
    )
    doc_splits = text_splitter.split_documents(documents)

    # Add chunk number to metadata
    for idx, split in enumerate(doc_splits):
        split.metadata["chunk"] = idx

    print(f"# of documents = {len(doc_splits)}")
    return doc_splits


def reformat(resp):
    """
    Reformats the response from the LLM.

    Args:
        resp (str): The response from the LLM.

    Returns:
        The reformatted response.
    """

    parameters = {
        "max_output_tokens": 1024,
        "temperature": 0.2,
        "top_p": 0.8,
        "top_k": 40,
    }
    model = TextGenerationModel.from_pretrained("text-bison")
    response = model.predict(
        """
Given the input text {0}, reformat it to make it clean and representable to be shown in HTML as search result on a website.
      """.format(
            resp
        ),
        **parameters,
    )
    return response.text


def formatter(result):
    """
    Formats the result of the QA chain.

    Args:
        result (dict): The result of the QA chain.

    Returns:
        The formatted result.
    """

    print(f"Query: {result['query']}")
    print("." * 80)
    references = []
    if "source_documents" in result.keys():
        for idx, ref in enumerate(result["source_documents"]):
            reference_item = {}
            print("-" * 80)
            print(f"REFERENCE #{idx}")
            reference_item["id"] = idx
            print("-" * 80)
            if "score" in ref.metadata:
                print(f"Matching Score: {ref.metadata['score']}")
                reference_item["matching_score"] = ref.metadata["score"]
            if "source" in ref.metadata:
                print(f"Document Source: {ref.metadata['source']}")
                reference_item["document_source"] = ref.metadata["source"]
            if "title" in ref.metadata:
                print(f"Document Name: {ref.metadata['title']}")
                reference_item["document_name"] = ref.metadata["title"]
            print("." * 80)
            print(f"Content: \n{wrap(ref.page_content)}")
            reference_item["page_content"] = wrap(ref.page_content)
            references.append(reference_item)
    print("." * 80)
    print(f"Response: {reformat(result['result'])}")
    print("." * 80)
    return reformat(result["result"]), references


def wrap(s):
    """
    Wraps the text to a width of 120.

    Args:
        s (str): The text to wrap.

    Returns:
        The wrapped text.
    """

    return "\n".join(textwrap.wrap(s, width=120, break_long_words=False))


def ask(query, qa, k, search_distance):
    """
    Asks a question to the QA chain.

    Args:
        query (str): The question to ask.
        qa (RetrievalQA): The QA chain to use.
        k (int): The number of results to return.
        search_distance (float): The search distance threshold.

    Returns:
        The formatted result.
    """

    qa.retriever.search_kwargs["search_distance"] = search_distance
    qa.retriever.search_kwargs["k"] = k
    result = qa({"query": query})
    print(result)
    return formatter(result)


@functions_framework.http
def qa_over_website(request):
    """
    Answers questions about the content of a website.

    Args:
        request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    request_json = request.get_json(silent=True)
    request_args = request.args

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

    # Set CORS headers for the main request
    headers = {"Access-Control-Allow-Origin": "*"}

    # query = request_json['sessionInfo']['parameters']['query']
    if request_json and "query" in request_json:
        query = request_json["query"]
    elif request_args and "query" in request_args:
        query = request_args["query"]
    elif request_json and "text" in request_json:
        query = request_json["text"]
    else:
        query = "Why should I choose Cymbal Bank?"

    PROJECT_ID = project_id  # @param {type:"string"}
    REGION = "us-central1"  # @param {type:"string"}

    # Initialize Vertex AI SDK
    vertexai.init(project=PROJECT_ID, location=REGION)

    LLM_MODEL = "text-bison@002"  # @param {type: "string"}
    MAX_OUTPUT_TOKENS = 1024  # @param {type: "integer"}
    TEMPERATURE = 0.2  # @param {type: "number"}
    TOP_P = 0.8  # @param {type: "number"}
    TOP_K = 40  # @param {type: "number"}
    VERBOSE = True  # @param {type: "boolean"}
    llm_params = dict(
        model_name=LLM_MODEL,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        top_k=TOP_K,
        verbose=VERBOSE,
    )

    llm = VertexAI(**llm_params)

    # Embeddings API integrated with langChain
    embeddings = VertexAIEmbeddings(model_name="textembedding-gecko@003")

    ME_REGION = "us-central1"
    # ME_INDEX_NAME = f"{PROJECT_ID}-me-index-3"  # @param {type:"string"}
    ME_EMBEDDING_DIR = f"{PROJECT_ID}-me-bucket-3"  # @param {type:"string"}
    # ME_DIMENSIONS = 768  # when using Vertex PaLM Embedding

    ME_INDEX_ID = "354891567120515072"
    ME_INDEX_ENDPOINT_ID = "7646923051275124736"
    print(f"ME_INDEX_ID={ME_INDEX_ID}")
    print(f"ME_INDEX_ENDPOINT_ID={ME_INDEX_ENDPOINT_ID}")

    # initialize vector store
    me = VectorSearchVectorStore.from_components(
        project_id=PROJECT_ID,
        region=ME_REGION,
        gcs_bucket_name=f"gs://{ME_EMBEDDING_DIR}".split("/")[2],
        embedding=embeddings,
        index_id=ME_INDEX_ID,
        endpoint_id=ME_INDEX_ENDPOINT_ID,
        stream_update=True,
    )

    # UNCOMMENT IF THIS TO UPDATE THE INDEX I.E. WHEN WEBPAGES ARE UPDATED OR NEW WEBPAGES ARE ADDED
    # documents = load_website_content()

    # doc_splits = chunk_documents(documents)
    # Store docs as embeddings in Matching Engine index
    # It may take a while since API is rate limited
    # texts = [doc.page_content for doc in doc_splits]
    # metadatas = [doc.metadata for doc in doc_splits]

    # doc_ids = me.add_texts(texts=texts, metadatas=metadatas)

    # Create chain to answer questions
    NUMBER_OF_RESULTS = 5  # randrandomint(8, 14)
    SEARCH_DISTANCE_THRESHOLD = 0.6

    # Expose index to the retriever
    retriever = me.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": NUMBER_OF_RESULTS,
            "search_distance": SEARCH_DISTANCE_THRESHOLD,
        },
    )

    prompt_template = """SYSTEM: You are an intelligent assistant helping the users of
    Cymbal Bank with their questions on services offered by the bank.

    Question: {question}

    Strictly Use ONLY the following pieces of context to answer the question at the end.
    Think step-by-step and then answer.
    Give a detailed and elaborate answer.
    Do not try to make up an answer:
    - If the answer to the question cannot be determined from the context alone,
    say "I cannot determine the answer to that."
    - If the context is empty, just say "I do not know the answer to that."

    =============
    {context}
    =============

    Question: {question}
    Helpful Answer:"""

    # Uses LLM to synthesize results from the search index.
    # Use Vertex PaLM Text API for LLM
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        verbose=True,
        chain_type_kwargs={
            "prompt": PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"],
            ),
        },
    )
    # Enable for troubleshooting
    qa.combine_documents_chain.verbose = True
    qa.combine_documents_chain.llm_chain.verbose = True
    qa.combine_documents_chain.llm_chain.llm.verbose = True

    response, ref = ask(query, qa, NUMBER_OF_RESULTS, SEARCH_DISTANCE_THRESHOLD)

    # remove duplicates from references
    references = []
    for i in ref:
        i.pop("id")
        if i not in references:
            references.append(i)

    print(response)
    print(references)
    references_str = json.dumps(references)
    res = {
        "fulfillment_response": {
            "messages": [{"text": {"text": [response, references_str]}}]
        }
    }
    return (res, 200, headers)
