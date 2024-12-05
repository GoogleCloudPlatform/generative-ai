import chromadb, json, os, pymupdf

from vertexai.generative_models import GenerativeModel, Part
import vertexai.preview.generative_models as generative_models
from google.cloud.aiplatform import pipeline_jobs
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from google.cloud import storage
from google import auth
from google.api_core import exceptions
from google.auth.transport import requests as google_auth_requests

from chromadb import Documents, EmbeddingFunction, Embeddings
import langchain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DataFrameLoader
import vertexai
import sys


class chroma_db():
  def __call__(self, input: Documents) -> Embeddings: # https://github.com/chroma-core/chroma/issues/1496
    embeddings = []
    for doc in input:
      vector = self.embed_model.get_embeddings([doc])
      embeddings.append(vector[0].values)
    return embeddings

  def __init__(self, name):
    self.name = name
    self.chunk_id = 0
    self.client = chromadb.Client()

  def create_collection(self, name, embedding_function, metadata):
    self.collection_name = name
    self.embedding_function = embedding_function
    self.collection = self.client.create_collection(
        name=name,
        embedding_function=embedding_function,
        metadata=metadata)

  def add_pdfs(self, local_pdf_folder):
    pdf_string_list = []
    for pdf in os.listdir(local_pdf_folder):
      pdf_text = ""
      with pymupdf.open(local_pdf_folder + pdf) as doc:
        for page in doc:
          pdf_text += page.get_text()
        pdf_string_list.append (pdf_text)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=10000,
        chunk_overlap=200)

    for pdf_text in pdf_string_list:
      chunks = text_splitter.split_text(pdf_text)
      for chunk in chunks:
        self.chunk_id+= 1
        self.collection.add(documents= [chunk], ids=f"chunk_{self.chunk_id}")



  def add_corpus_jsonl(self, training_data_loc = "./downloaded_files/"):
    with open(training_data_loc + "corpus.jsonl", "r") as f:
      for line in f:
        data = json.loads(line)
        self.collection.add(documents= [data["text"]], ids=data["_id"])
      print("All Chunks loaded!") #<Zthor>




class Vanilla_Embedding_Model(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings: # https://github.com/chroma-core/chroma/issues/1496
      embeddings = []
      for doc in input:
        vector = self.embed_model.get_embeddings([doc])
        embeddings.append(vector[0].values)
      return embeddings

    def __init__(self, model_name= "text-embedding-004"):
        self.embed_model = TextEmbeddingModel.from_pretrained(model_name)