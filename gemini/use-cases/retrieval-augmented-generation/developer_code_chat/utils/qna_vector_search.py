# Copyright 2023 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Answer QnA Type Questions using genai Content"""

# Utils
import configparser
import json
import logging
import subprocess
import grpc
import numpy as np

from langchain.chains import RetrievalQA
from langchain.llms import VertexAI
from langchain.prompts import PromptTemplate

import vertexai
from vertexai.generative_models import GenerativeModel

from utils.generate_embeddings_utils import CustomVertexAIEmbeddings
from utils.vector_search import VectorSearch
from utils.vector_search_utils import VectorSearchUtils


class QnAVectorSearch:
    """genai Generate Answer From genai Content"""

    def __init__(
        self, config_file: str = "config.ini", logger=logging.getLogger()
    ) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.project_id = self.config["default"]["project_id"]
        self.region = self.config["default"]["region"]
        self.me_region = self.config["embedding"]["me_region"]
        self.me_index_name = self.config["embedding"]["me_index_name"]
        self.me_embedding_dir = self.config["embedding"]["me_embedding_dir"]
        self.number_of_references_to_summarise = int(
            self.config["genai_qna"]["number_of_references_to_summarise"]
        )
        self.search_distance_threshould = float(
            self.config["genai_qna"]["search_distance_threshould"]
        )
        self.logger = logger

    def get_reference_details(self, result):
        """Get references and their details"""

        reference_logs = []  # {result:, reference: [{pdf, page, score}, {}]}
        if len(result["source_documents"]) == 0:
            return "", reference_logs
        ref_text = "Reference:\n"
        number_of_references_to_show = int(
            self.config["genai_qna"]["number_of_references_to_show"]
        )
        for idx, ref in enumerate(
            result["source_documents"][:number_of_references_to_show]
        ):
            page_no = int(ref.metadata["page_number"]) + 1
            source = (
                "https://storage.mtls.cloud.google.com/"
                + ref.metadata["source"].split("gs://")[-1]
            )

            reference_logs.append(
                {
                    "gcs_file_path": ref.metadata["source"]
                    + "/"
                    + ref.metadata["document_name"],
                    "page": page_no,
                    "score": np.round(ref.metadata["score"], 2),
                }
            )

            ref_text += f""" {str(idx+1)}. <a href="{source}/{ref.metadata['document_name']}#page={page_no}">{ref.metadata['document_name']}</a> (Page : {page_no})\n"""  # pylint:disable=line-too-long
        return ref_text, reference_logs

    def configure_retrievalqa_chain(
        self,
        llm,
        retriever,
        template,
        search_distance_threshould,
        number_of_references_to_summarise,
    ):
        """Uses LLM to synthesize results from the search index."""
        qa = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            verbose=True,
            chain_type_kwargs={
                "prompt": PromptTemplate(
                    template=template,
                    input_variables=["context", "question"],
                ),
            },
        )

        # Enable for troubleshooting
        qa.combine_documents_chain.verbose = True
        qa.combine_documents_chain.llm_chain.verbose = True
        qa.combine_documents_chain.llm_chain.llm.verbose = True

        # setting threshold limits
        qa.retriever.search_kwargs["search_distance"] = search_distance_threshould
        qa.retriever.search_kwargs["k"] = number_of_references_to_summarise

        return qa

    def get_token_length(self, project, model, message):
        """Get Token Length using curl command"""
        # The python sdk is not available at the time of development
        # Using curl command for the same.
        if len(message.split(" ")) < 20:
            return len(message.split(" "))
        m_json = {"instances": [{"prompt": message}]}
        with open(file="request_message.json", mode="w", encoding="utf-8") as f:
            json.dump(m_json, f)
        curl_command = f'''curl -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json; charset=utf-8" -d @request_message.json "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/us-central1/publishers/google/models/{model}:countTokens"'''  # pylint:disable=line-too-long
        output = json.loads(subprocess.check_output(curl_command, shell=True))

        return output["totalTokens"]

    def ask_qna(self, query="what is java"):
        """Get relevent responce from intra-documents"""
        # Initialize Vertex AI SDK
        vertexai.init(project=self.project_id, location=self.region)

        # Text model instance integrated with langChain
        # Default model
        model_name = self.config["genai_qna"]["model_name"]
        max_output_tokens = int(self.config["genai_qna"]["max_output_tokens"])

        # Check token length of input message
        # input_token_len = self.get_token_length(self.project_id, \
        # model_name, query)

        model = GenerativeModel(self.config["genai_qna"]["model_name"])
        input_token_len = model.count_tokens(query).total_tokens
        self.logger.info("QnA: Input_token_len for QnA: %s", input_token_len)

        self.logger.info("QnA: Using model for QnA: %s", model_name)
        llm = VertexAI(
            model_name=model_name,
            max_output_tokens=max_output_tokens,
            temperature=float(self.config["genai_qna"]["temperature"]),
            top_p=float(self.config["genai_qna"]["top_p"]),
            top_k=int(self.config["genai_qna"]["top_k"]),
            verbose=False,
        )

        # Embeddings API integrated with langChain
        embeddings = CustomVertexAIEmbeddings(
            requests_per_minute=int(self.config["embedding"]["embedding_qpm"]),
            num_instances_per_batch=int(
                self.config["embedding"]["embedding_num_batch"]
            ),
        )

        mengine = VectorSearchUtils(self.project_id, self.me_region, self.me_index_name)
        me_index_id, me_index_endpoint_id = mengine.get_index_and_endpoint()

        # initialize vector store
        me = VectorSearch.from_components(
            project_id=self.project_id,
            region=self.me_region,
            gcs_bucket_name=f"gs://{self.me_embedding_dir}".split("/")[2],
            embedding=embeddings,
            index_id=me_index_id,
            endpoint_id=me_index_endpoint_id,
        )

        # STEP 1: Retrieval based Question/Answering Chain
        # Expose index to the retriever
        retriever = me.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": self.number_of_references_to_summarise,
                "search_distance": self.search_distance_threshould,
            },
        )

        # Customize the default retrieval prompt template
        template = """
        SYSTEM: You are genai Programming Language Learning Assistant helping the students answer their questions based on following context. Explain the answers in detail for students.

        Instructions:
        1. Think step-by-step and then answer.
        2. Explain the answer in detail.
        3. If the answer to the question cannot be determined from the context alone, say "I cannot determine the answer to that."
        4. If the context is empty, just say "I could not find any references that are directly related to your question."

        Context:
        =============
        {context}
        =============

        What is the Detailed explanation of answer of following question?
        Question: {question}
        Detailed explanation of Answer:"""  # pylint: disable=line-too-long

        # Configure RetrievalQA chain
        result = None
        try:
            qa = self.configure_retrievalqa_chain(
                llm,
                retriever,
                template,
                self.search_distance_threshould,
                self.number_of_references_to_summarise,
            )
            result = qa({"query": query})
        except grpc.RpcError as e:  # pylint:disable=C0103
            self.logger.error(
                "QnA: Token limit exceeded, reducing the reference contexts \
                and retying again.."
            )
            self.logger.info(e)
            try:
                qa = self.configure_retrievalqa_chain(
                    llm, retriever, template, self.search_distance_threshould, 2
                )
                result = qa({"query": query})
            except Exception as exp:  # pylint: disable=W0718,W0703
                self.logger.error("QnA: Exception raised :%s", exp)
                return {
                    "is_answer": False,
                    "answer": "Please reduce question length and rephrase.",
                    "answer_reference": None,
                    "reference_logs": [],
                    "llm_model": model_name,
                }
        except Exception as e:  # pylint: disable=W0718,W0703,C0103
            self.logger.error("QnA: Exception while generating responce in QnA. %s", e)

        self.logger.info("QnA: raw response:\n %s", result)
        if result:
            result["result"] = result["result"].replace("\n", " ").replace("  ", " ")

            if "I cannot determine the answer to that." in result["result"]:
                return {
                    "is_answer": False,
                    "answer": "",
                    "answer_reference": None,
                    "reference_logs": [],
                    "llm_model": model_name,
                    "llm_error_msg": None,
                }
            else:
                ref_text, reference_logs = self.get_reference_details(result)
                return {
                    "is_answer": True,
                    "answer": result["result"],
                    "answer_reference": ref_text,
                    "reference_logs": reference_logs,
                    "llm_model": model_name,
                    "llm_error_msg": None,
                }
        return {
            "is_answer": False,
            "answer": "",
            "answer_reference": None,
            "reference_logs": [],
            "llm_model": model_name,
            "llm_error_msg": None,
        }


if __name__ == "__main__":
    genai_qna = QnAVectorSearch(config_file="config.ini")
    print(genai_qna.ask_qna())
