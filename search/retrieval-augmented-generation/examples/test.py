import os
from concurrent.futures import ThreadPoolExecutor

import requests
import itertools
import numpy as np
import pandas as pd
import numpy.linalg
import vertexai

from google.api_core import retry
from vertexai.language_models import TextEmbeddingModel, TextGenerationModel
from tqdm.auto import tqdm
from bs4 import BeautifulSoup, Tag


# Given a Google documentation URL, retrieve a list of all text chunks within h2 sections
def get_sections(url: str) -> list[str]:
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    sections = []
    paragraphs = []

    body_div = soup.find("div", class_="devsite-article-body")
    for child in body_div.findChildren():
        if child.name == "p":
            paragraphs.append(child.get_text().strip())
        if child.name == "h2":
            sections.append(" ".join(paragraphs))
            break

    for header in soup.find_all("h2"):
        paragraphs = []
        nextNode = header.nextSibling
        while nextNode:
            if isinstance(nextNode, Tag):
                if nextNode.name in {"p", "ul"}:
                    paragraphs.append(nextNode.get_text().strip())
                elif nextNode.name == "h2":
                    sections.append(" ".join(paragraphs))
                    break
            nextNode = nextNode.nextSibling
    return sections


def process_url(url):
    file_name = os.path.basename(url)
    page = requests.get(url)
    if page.content:
        with open(
            f"/Users/holtskinner/Downloads/docs_html/{file_name}.html", "wb"
        ) as f:
            f.write(page.content)

    # sections = get_sections(url)
    # if sections:
    #     with open(f"/Users/holtskinner/Downloads/docs_output/{file_name}.txt", "w") as f:
    #         f.write("\n".join(sections))


import os
import glob
import json
import pandas as pd

from vertexai.preview.language_models import TextEmbeddingModel

if __name__ == "__main__":
    with open("URLs.txt", "r") as f:
        URLS = [line.strip() for line in f.readlines()]

    with ThreadPoolExecutor() as executor:
        executor.map(process_url, URLS)

    # files = glob.glob("/Users/holtskinner/Downloads/docs_output/*.txt")
    # jsonl = []
    # for file in files:
    #     with open(file, "r") as f:
    #         json_string = json.dumps({"content": f.read()})
    #         jsonl.append(f"{json_string}\n")

    # with open("/Users/holtskinner/Downloads/test_table.jsonl", "w") as f:
    #     f.writelines(jsonl)
    # textembedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko")
    # batch_prediction_job = textembedding_model.batch_predict(
    #     dataset=["gs://ucs-demo/gen-ai-cloud-docs/test_table.jsonl"],
    #     destination_uri_prefix="gs://ucs-demo/gen-ai-cloud-docs/tmp/",
    # )
    # print(batch_prediction_job.display_name)
    # print(batch_prediction_job.resource_name)
    # print(batch_prediction_job.state)

    # files = glob.glob("/Users/holtskinner/Downloads/docs_output/*.txt")

    # input_contents = {}
    # for file in files:
    #     file_name = os.path.basename(file)
    #     id_ = os.path.splitext(file_name)[0]
    #     with open(file, "r") as f:
    #         input_content = f.read()
    #         input_contents[input_content] = id_

    # embeddings_file = "/Users/holtskinner/Downloads/000000000000.jsonl"
    # emb_df = pd.read_json(path_or_buf=embeddings_file, lines=True, orient="records")

    # vais_embeddings = []
    # for i, emb in emb_df.iterrows():
    #     if emb["status"]:
    #         print(f"Skipping row {i}")
    #         continue

    #     try:
    #         embeddings = emb["predictions"][0]["embeddings"]
    #     except TypeError as exc:
    #         print(f"Exception! Row {i}")
    #         print(emb)
    #         raise exc
    #     if embeddings["statistics"]["truncated"]:
    #         print(emb["instance"]["content"])
    #         print("\n\n")
    #         continue
    #     id_ = input_contents[emb["instance"]["content"]]

    #     uri = f"gs://ucs-demo/gen-ai-cloud-docs/docs_html/{id_}.html"
    #     vais_embeddings.append({
    #         "id": id_,
    #         "content": {
    #             "mimeType": "text/html",
    #             "uri": uri
    #         },
    #         "structData": {
    #             "embedding_vector": embeddings["values"],
    #         },
    #     })

    # with open("output_embeddings.jsonl", "w", encoding="utf-8") as json_file:
    #     for record in vais_embeddings:
    #         json.dump(record, json_file, ensure_ascii=False)
    #         json_file.write("\n")

# {"id":"doc-3","structData":{"title":"test_doc_3","description":"This is document uses a yellow color theme","color_theme":"yellow"},"content":{"mimeType":"application/pdf","uri":"gs://test-bucket-12345678/test_doc_4.pdf"}}
