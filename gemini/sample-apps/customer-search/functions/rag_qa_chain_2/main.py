import json
import os
from os import environ
import textwrap

# Utils
import time
from typing import List
import urllib.request

import functions_framework

# from langchain.agents import AgentType, initialize_agent
from langchain.agents import tool
from langchain.chains import RetrievalQA
from langchain.document_loaders import WebBaseLoader
from langchain.embeddings import VertexAIEmbeddings
from langchain.llms import VertexAI
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
import nest_asyncio
from utils.matching_engine import MatchingEngine
from utils.matching_engine_utils import MatchingEngineUtils
import vertexai
from vertexai.language_models import TextGenerationModel

# Vertex AI

# LangChain


project_id = environ.get("PROJECT_ID")

# Import custom Matching Engine packages
# with httpimport.remote_repo('https://github.com/GoogleCloudPlatform/generative-ai/tree/main/language/use-cases/document-qa'):
#     import utils
#     from utils.matching_engine import MatchingEngine
#     from utils.matching_engine_utils import MatchingEngineUtils


def init_me_libs():
    if not os.path.exists("utils"):
        os.makedirs("utils")

    url_prefix = "https://raw.githubusercontent.com/GoogleCloudPlatform/generative-ai/main/language/use-cases/document-qa/utils"
    files = ["__init__.py", "matching_engine.py", "matching_engine_utils.py"]

    for fname in files:
        urllib.request.urlretrieve(f"{url_prefix}/{fname}", filename=f"utils/{fname}")


init_me_libs()


def load_website_content():
    nest_asyncio.apply()

    loader = WebBaseLoader(
        [
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/home",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/pay/money-transfer/neft",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/pay/money-transfer/upi",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/pay/money-transfer/imps",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/pay/cards/debit-card",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/pay/cards/credit-card",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/pay/bills/recharge-mobile-dth-broadband",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/pay/bills/electricity",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/pay/bills/insurance-premium",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/save/account/saving",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/save/account/current",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/save/account/salary",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/save/deposits/fixed-deposit",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/save/deposits/recurring-deposit",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/invest/open-demat-account",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/invest/bonds/sovereign-gold-bond",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/invest/bonds/savings-bond",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/invest/equities-and-derivatives",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/invest/mutual-funds",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/insure/life-insurance/secure-childrens-future",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/insure/life-insurance/protect-life-term",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/insure/health-accident/mediclaim",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/insure/health-accident/personal-accident",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/insure/vehicle/two-wheeler",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/insure/vehicle/car",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/insure/travel",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/borrow/loans/personal-loan",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/borrow/loans/home-loan",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/borrow/loans/business-loan",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/borrow/loans/car-loan",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/borrow/loans/two-wheeler-loan",
            "https://sites.google.com/pranshusingh.altostrat.com/cymbalbank/borrow/loans/education-loan",
        ]
    )
    loader.requests_per_second = 1

    documents = loader.aload()
    return documents


def chunk_documents(documents):
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
    return "\n".join(textwrap.wrap(s, width=120, break_long_words=False))


def ask(query, qa, k, search_distance):
    qa.retriever.search_kwargs["search_distance"] = search_distance
    qa.retriever.search_kwargs["k"] = k
    result = qa({"query": query})
    print(result)
    return formatter(result)


def ask_react(query, react_agent):
    result = react_agent.run(query)
    print(result)
    return formatter(result)


@tool
def enterprise_search(query: str):
    """
    Use this tool to find information in documents.
    Args:
    query: Analyse the conversation to come up with the parameter. This is the current problem the user is trying to solve.
    """
    return ask(query)


# Utility functions for Embeddings API with rate limiting
def rate_limit(max_per_minute):
    period = 60 / max_per_minute
    print("Waiting")
    while True:
        before = time.time()
        yield
        after = time.time()
        elapsed = after - before
        sleep_time = max(0, period - elapsed)
        if sleep_time > 0:
            print(".", end="")
            time.sleep(sleep_time)


class BaseModelMixin:
    requests_per_minute: int
    num_instances_per_batch: int

    # Overriding embed_documents method
    def embed_documents(self, texts: List[str]):
        limiter = rate_limit(self.requests_per_minute)
        results = []
        docs = list(texts)

        while docs:
            # Working in batches because the API accepts maximum 5
            # documents per request to get embeddings
            head, docs = (
                docs[: self.num_instances_per_batch],
                docs[self.num_instances_per_batch :],
            )
            chunk = self.client.get_embeddings(head)
            results.extend(chunk)
            next(limiter)

        return [r.values for r in results]


class CustomVertexAIEmbeddings(VertexAIEmbeddings, BaseModelMixin):
    pass


@functions_framework.http
def hello_http(request):
    # init_me_libs()

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

    LLM_MODEL = "text-bison"  # @param {type: "string"}
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
    EMBEDDING_QPM = 100
    EMBEDDING_NUM_BATCH = 5
    embeddings = CustomVertexAIEmbeddings(
        requests_per_minute=EMBEDDING_QPM,
        num_instances_per_batch=EMBEDDING_NUM_BATCH,
    )

    ME_REGION = "us-central1"
    ME_INDEX_NAME = f"{PROJECT_ID}-me-index"  # @param {type:"string"}
    ME_EMBEDDING_DIR = f"{PROJECT_ID}-me-bucket"  # @param {type:"string"}
    # ME_DIMENSIONS = 768  # when using Vertex PaLM Embedding

    mengine = MatchingEngineUtils(PROJECT_ID, ME_REGION, ME_INDEX_NAME)

    ME_INDEX_ID, ME_INDEX_ENDPOINT_ID = mengine.get_index_and_endpoint()
    print(f"ME_INDEX_ID={ME_INDEX_ID}")
    print(f"ME_INDEX_ENDPOINT_ID={ME_INDEX_ENDPOINT_ID}")

    # initialize vector store
    me = MatchingEngine.from_components(
        project_id=PROJECT_ID,
        region=ME_REGION,
        gcs_bucket_name=f"gs://{ME_EMBEDDING_DIR}".split("/")[2],
        embedding=embeddings,
        index_id=ME_INDEX_ID,
        endpoint_id=ME_INDEX_ENDPOINT_ID,
    )

    # UNCOMMENT IF THIS TO UPDATE THE INDEX I.E. WHEN WEBPAGES ARE UPDATED OR NEW WEBPAGES ARE ADDED
    # documents = load_website_content()

    # doc_splits = chunk_documents(documents)
    # Store docs as embeddings in Matching Engine index
    # It may take a while since API is rate limited
    # texts = [doc.page_content for doc in doc_splits]
    # metadatas = [
    #     [
    #         {"namespace": "source", "allow_list": [doc.metadata["source"]]},
    #         {"namespace": "title", "allow_list": [doc.metadata["title"]]},
    #         {"namespace": "chunk", "allow_list": [str(doc.metadata["chunk"])]},
    #     ]
    #     for doc in doc_splits
    # ]

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

    prompt_template = """SYSTEM: You are an intelligent assistant helping the users of Cymbal Bank with their questions on services offered by the bank.

    Question: {question}

    Strictly Use ONLY the following pieces of context to answer the question at the end. Think step-by-step and then answer. Give a detailed and elaborate answer.
    Do not try to make up an answer:
    - If the answer to the question cannot be determined from the context alone, say "I cannot determine the answer to that."
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

    # react_agent = initialize_agent(
    #     llm=llm,
    #     tools=[enterprise_search],
    #     agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    #     verbose=True,
    # )
    # response, ref = ask_react(query, react_agent)

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
