# Copyright 2023 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Generate Embeddings of PDF Documents"""

import configparser

# Utils
import json
import logging
import uuid

from google.cloud import aiplatform, storage
import numpy as np
from utils.gcs_directory_loader import GCSDirectoryLoader
from utils.gcs_file_loader import GCSFileLoader
from utils.generate_embeddings_utils import (
    CustomVertexAIEmbeddings,
    check_if_doc_needs_fix,
    split_documents,
)
from utils.vector_search import VectorSearch
from utils.vector_search_utils import VectorSearchUtils
import vertexai

logging.basicConfig(level=logging.INFO)


class GenerateEmbeddings:
    """Generate Embeddings: Create, Deploy"""

    def __init__(
        self, config_file: str = "config.ini", logger=logging.getLogger()
    ) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        self.project_id = self.config["default"]["project_id"]
        self.gcs_bucket_docs = self.config["embedding"]["me_embedding_dir"]
        self.me_region = self.config["embedding"]["me_region"]
        self.me_index_name = self.config["embedding"]["me_index_name"]
        self.me_embedding_dir = self.config["embedding"]["me_embedding_dir"]

        self.logger = logger
        self.storage_bucket_setup()

    def create_dummy_embeddings(self):
        """Create Dummy Embedding"""

        init_embedding = {
            "id": str(uuid.uuid4()),
            "embedding": list(np.zeros(int(self.config["embedding"]["me_dimensions"]))),
        }

        # dump embedding to a local file
        with open(file="embeddings_0.json", mode="w", encoding="utf-8") as f:
            json.dump(init_embedding, f)

    def storage_bucket_setup(self):
        """Setup storage bucket if not already done"""
        
        self.logger.info("GenEmb: Checking storage bucket setup")
        storage_client = storage.Client()
        self.bucket = storage_client.bucket(self.me_embedding_dir)
        if self.bucket.exists():
            self.logger.info(
                "GenEmb: GCS bucket already exists: %s", self.me_embedding_dir
            )
        else:
            ## create new GCS bucket
            self.bucket = storage_client.create_bucket(
                bucket_or_name=self.me_embedding_dir,
                project=self.project_id,
                location=self.config["embedding"]["me_embedding_region"],
            )
            self.logger.info("GenEmb: New storage bucket: %s", self.me_embedding_dir)

            # dummy_embeddings
            self.create_dummy_embeddings()

            ## move dummy embeddings file
            blob = self.bucket.blob("init_index/embeddings_0.json")
            blob.upload_from_filename("embeddings_0.json")
            self.logger.info(
                "GenEmb: Moved dummy embeddings file to the storage bucket"
            )

    def create_index(self):
        """Create Index to vector search"""

        mengine = VectorSearchUtils(self.project_id, self.me_region, self.me_index_name)

        list_indexes = aiplatform.MatchingEngineIndex.list(
            filter=f"display_name={self.me_index_name}"
        )
        if list_indexes:
            self.logger.info("GenEmb: Found Index from previous run..")
            index = list_indexes[0]
        else:
            self.logger.info("GenEmb: Index not available, creating new..")
            index = mengine.create_index(
                embedding_gcs_uri=f"gs://{self.me_embedding_dir}/init_index",
                dimensions=int(self.config["embedding"]["me_dimensions"]),
                index_update_method="streaming",
                index_algorithm="tree-ah",
            )
            if index:
                self.logger.info("GenEmb: Created Index: %s", index.name)
        return mengine

    def deploy_index(self, m_engine):
        """Deploy Index to vector search"""

        list_endpoints = aiplatform.MatchingEngineIndexEndpoint.list(
            filter=f"display_name={self.me_index_name}-endpoint"
        )
        if list_endpoints:
            endpoint = list_endpoints[0]
            self.logger.info("GenEmb: Found Endpoint from previous run %s", endpoint)
        else:
            self.logger.info("Creating new endpoint.")
            index_endpoint = m_engine.deploy_index()
            if index_endpoint:
                self.logger.info(
                    "GenEmb: Index endpoint resource : %s", index_endpoint.name
                )
                self.logger.info(
                    "GenEmb: Index endpoint public domain name : %s",
                    index_endpoint.public_endpoint_domain_name,
                )
                self.logger.info("GenEmb: Deployed indexes to endpoint:")
                for d in index_endpoint.deployed_indexes:
                    self.logger.info(d.id)

    def ingest_multiple_pdf_documents(self):
        """Ingest PDF files from a folder in gcs bucket"""

        loader = GCSDirectoryLoader(
            project_name=self.project_id,
            bucket=self.gcs_bucket_docs,
            prefix=self.config["embedding"]["index_folder_prefix"],
        )
        documents = loader.load()

        return documents

    def ingest_single_pdf_document(self):
        """Ingest single PDF file directly"""

        loader = GCSFileLoader(
            self.project_id,
            self.gcs_bucket_docs,
            self.config["embedding"]["index_single_file_path"],
        )
        
        documents = loader.load()

        return documents

    def process_documents(self, documents):
        """Process Individual Documents"""

        # Check if any of the document content is empty and remove them
        empty_content_idx = []
        doc_index = check_if_doc_needs_fix(documents)
        while doc_index != -1:
            empty_content_idx.append(documents[doc_index])
            documents.pop(doc_index)
            doc_index = check_if_doc_needs_fix(documents)
        self.logger.info(
            "GenEmb: # docs with empty content : %s", len(empty_content_idx)
        )

        # Add document name and source to the metadata
        no_document_name = []

        for doc_index, document in enumerate(documents):
            documents[doc_index].page_content = document.page_content.replace("\t", " ")

            doc_md = document.metadata

            if "document_name" in doc_md.keys():
                document_name = doc_md["document_name"]
            else:
                # Document_name not in metadata
                no_document_name.append(doc_md["source"])
                if ".pdf" in doc_md["source"]:
                    document_name = doc_md["source"].split("/")[-1]

            if "source" in doc_md.keys():
                if ".pdf" in doc_md["source"]:
                    source = "/".join(doc_md["source"].split("/")[:-1])
                else:
                    # derive doc source from Document loader
                    doc_source_prefix = "/".join(self.gcs_bucket_docs.split("/")[:3])
                    doc_source_suffix = "/".join(doc_md["source"].split("/")[3:-1])
                    source = f"{doc_source_prefix}/{doc_source_suffix}"
            else:
                self.logger.info("GenEmb: source not in metadata %s", doc_md)
                continue

            if "page" in doc_md.keys() or "page_number" in doc_md.keys():
                page_number = (
                    doc_md["page"] if "page" in doc_md.keys() else doc_md["page_number"]
                )
            else:
                self.logger.info("GenEmb: No page in metadata %s", doc_md)
                continue

            documents[doc_index].metadata["source"] = source
            documents[doc_index].metadata["document_name"] = document_name
            documents[doc_index].metadata["page_number"] = page_number + 1

        self.logger.info(
            "GenEmb: # docs without proper filename were : %s", len(no_document_name)
        )

        self.logger.info("\nGenEmb: Splitting the documents..")
        self.logger.info(
            "GenEmb: split_document_flag : %s",
            self.config["embedding"]["split_document_flag"],
        )
        doc_splits = split_documents(
            documents, self.config["embedding"]["split_document_flag"]
        )

        return doc_splits

    def configure_matching_engine(self, m_engine, embeddings):
        """Initialize vector store"""

        me_index_id, me_index_endpoint_id = m_engine.get_index_and_endpoint()

        me = VectorSearch.from_components(
            project_id=self.project_id,
            region=self.me_region,
            gcs_bucket_name=f"gs://{self.me_embedding_dir}".split("/")[2],
            embedding=embeddings,
            index_id=me_index_id,
            endpoint_id=me_index_endpoint_id,
        )
        return me

    def add_embeddings_to_vector_store(self, me, doc_splits):
        """Store docs as embeddings in Matching Engine index"""
        # It may take a while since API is rate limited
        texts = [doc.page_content for doc in doc_splits]
        metadatas = [
            [
                {"namespace": "source", "allow_list": [doc.metadata["source"]]},
                {
                    "namespace": "document_name",
                    "allow_list": [doc.metadata["document_name"]],
                },
                {
                    "namespace": "chunk",
                    "allow_list": [str(doc.metadata["chunk"])],
                },
                {
                    "namespace": "page_number",
                    "allow_list": [str(doc.metadata["page"])]
                    if "page" in doc.metadata.keys()
                    else [str(doc.metadata["page_number"])],
                },
            ]
            for doc in doc_splits
        ]

        doc_ids = me.add_texts(texts=texts, metadatas=metadatas)

        return doc_ids

    def generate_embeddings(self):
        """Generate new embeddings and save them in vector search"""
        ## Initialize Vertex AI SDK
        vertexai.init(
            project=self.project_id, location=self.config["default"]["region"]
        )

        # Embeddings API integrated with langChain
        embeddings = CustomVertexAIEmbeddings(
            requests_per_minute=int(self.config["embedding"]["embedding_qpm"]),
            num_instances_per_batch=int(
                self.config["embedding"]["embedding_num_batch"]
            ),
        )

        ## STEP 1: Create Matching Engine Index and Endpoint for Retrieval
        mengine = self.create_index()
        self.deploy_index(mengine)

        ## STEP 2: Add Document Embeddings to Matching Engine - Vector Store
        self.logger.info("GenEmb: Loading the document(s)..")
        documents = []
        if self.config["embedding"]["index_single_file_flag"] == "True":
            documents = self.ingest_single_pdf_document()
        else:
            documents = self.ingest_multiple_pdf_documents()

        self.logger.info("GenEmb: Processing the documents..:%s", len(documents))
        doc_splits = self.process_documents(documents)

        ## Configure Matching Engine as Vector Store
        me = self.configure_matching_engine(mengine, embeddings)

        _ = self.add_embeddings_to_vector_store(me, doc_splits)

        self.logger.info("\nGenEmb: Embeddings successfully created/updated ..")


if __name__ == "__main__":
    generate_embeddings = GenerateEmbeddings(config_file="config.ini")
    generate_embeddings.generate_embeddings()
