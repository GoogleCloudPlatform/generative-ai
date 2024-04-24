# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Generative AI Models based functions to respond questions"""

import configparser

# Utils
import json
import logging
from typing import List

from google.cloud import aiplatform
from utils.qna_vector_search import QnAVectorSearch
from vertexai.generative_models import GenerationConfig, GenerativeModel


class IntentRouting:
    """genai Assistant"""

    def __init__(
        self,
        model: GenerativeModel,
        index_endpoint: aiplatform.MatchingEngineIndexEndpoint,
        deployed_index_id: str,
        config_file: str = "config.ini",
        logger=logging.getLogger(),
    ) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        self.logger = logger
        self.model = model
        self.index_endpoint = index_endpoint
        self.deployed_index_id = deployed_index_id

        self.genai_qna = QnAVectorSearch(
            model=model,
            index_endpoint=index_endpoint,
            deployed_index_id=deployed_index_id,
            config_file=config_file,
            logger=logger,
        )

        self.genai_qna_parameters = GenerationConfig(
            temperature=float(self.config["genai_qna"]["temperature"]),
            max_output_tokens=int(self.config["genai_qna"]["max_output_tokens"]),
            top_p=float(self.config["genai_qna"]["top_p"]),
            top_k=int(self.config["genai_qna"]["top_k"]),
        )

        self.genai_chat_parameters = GenerationConfig(
            temperature=float(self.config["genai_chat"]["temperature"]),
            max_output_tokens=int(self.config["genai_chat"]["max_output_tokens"]),
        )

    def greetings(self, text: str) -> str:
        """
        Generates a friendly greeting message in response to a 'WELCOME' intent.

        Leverages the provided chat model to generate a greeting tailored to the enabled programming languages.

        Args:
            text (str): The user's original message.

        Returns:
            str: The generated greeting message.
        """

        enabled_programming_language_list = self.config["default"][
            "enabled_programming_language"
        ].split(",")
        enabled_programming_language = ", ".join(
            [lang.title() for lang in enabled_programming_language_list]
        )

        chat = self.model.start_chat()
        response = chat.send_message(
            f"""You are Generative AI powered genai Learning Assistant.

        You are trained ONLY to answers questions related to following programming languages: {enabled_programming_language}

        Write a brief greeting message:"""
        )
        parameters_local = GenerationConfig(
            temperature=0.7,
            max_output_tokens=int(self.config["genai_chat"]["max_output_tokens"]),
        )

        response = chat.send_message(f"""{text}""", generation_config=parameters_local)
        message = response.text
        return message

    def closing(self, text: str) -> str:
        """
        Generates a closing/thank you message in response to a 'CLOSE' intent.

        Leverages the provided chat model to generate a closing message.

        Args:
            text (str): The user's original message.

        Returns:
            str: The generated closing message.
        """

        parameters_local = GenerationConfig(
            temperature=0.7,
            max_output_tokens=int(self.config["genai_chat"]["max_output_tokens"]),
        )
        chat = self.model.start_chat()
        response = chat.send_message(
            """You are Generative AI powered genai Learning Assistant.
                Write a brief closing thank you message:"""
        )
        response = chat.send_message(f"""{text}""", generation_config=parameters_local)
        message = response.text
        return message

    def genai_classify_intent(self, text: str) -> str:
        """
        Classifies the intent of an incoming message using a strict intent classifier model.

        The supported intents are:
            * 'WELCOME'
            * 'WRITE_CODE'
            * 'PROGRAMMING_QUESTION_AND_ANSWER'
            * 'CLOSE'
            * 'OTHER'
            * 'FOLLOWUP'

        Args:
            text (str): The user's message.

        Returns:
            str: The classified intent.
        """

        response = self.model.generate_content(
            f"""
            You are strict intent classifier , Classify intent of messages into 5 categories

            Instructions:
            1. Classify the intents into one of these categories only: 'WELCOME', 'WRITE_CODE', 'PROGRAMMING_QUESTION_AND_ANSWER', 'CLOSE', 'OTHER', 'FOLLOWUP'.
            2. Messages can be read as case-insensitive.
            3. Reply ONLY with category of intent. Don't generate additional intent outside of this list.

            Definition of Intents:
            1. WELCOME : is the category with greeting message and to know about the assistant for example hi, hey there, Hello, Good morning, good afternoon, good evening, who are you?, what prgramming languesges do you know?, what do you do?, how can you help me?.
            2. WRITE_CODE : is the category with code writing , debugging, explain code message. user wants you to write a code.
            3. PROGRAMMING_QUESTION_AND_ANSWER: is the category with strictly programming language related descriptive or theoretical questions. Any other question non related to programming should go into others.
            4. CLOSE : is the category for closing the chat with messages like okay THANKS!, bye, Thanks, thank you, goodbye.
            5. OTHER : is the category where user is asking non information technology related quesiontion. for example Who is PM of india, what happended in G20 summit.
            6. FOLLOWUP : is the category with user is asking the followup questions like, such as write a code for same, give me the code for above, give me example, explain in detail, what above method is doing etc..

            Examples:
            MESSAGE: Hi
            INTENT: WELCOME

            MESSAGE: What is the difference between list and set?
            INTENT: PROGRAMMING_QUESTION_AND_ANSWER

            MESSAGE: Fix the error in below code:
            def create_dataset(id: str): -> None
            ...

            SyntaxError: invalid syntax
            INTENT: WRITE_CODE

            What is the intent of the below message?
            MESSAGE:{text}
            INTENT:""",  # pylint: disable=C0301:line-too-long
            generation_config=self.genai_qna_parameters,
        )

        if response.to_dict()["candidates"][0]["finish_reason"] != 1:
            self.logger.info(
                "classify_intent: No response from QnA due to LLM safety checks."
            )
            self.logger.info("LLM error code: %s\n", response.raw_prediction_response)

        intent = response.text
        return (
            str(intent).replace('"', "").replace("'", "").replace("INTENT:", "").strip()
        )

    def ask_codey(self, text: str) -> str:
        """
        Generates code in response to code-related questions ('WRITE_CODE' intent).

        Provides instructions to the chat model, handles potential errors (e.g., unclear questions, unsupported programming languages), and formats the generated code.

        Args:
            text (str): The user's code-related query.

        Returns:
            str: The generated code (or an error message if applicable).
        """

        unable_to_understand_question = self.config["error_msg"][
            "unable_to_understand_question"
        ]
        non_programming_question_error_msg = self.config["error_msg"][
            "non_programming_question_error_msg"
        ]
        enabled_programming_language = self.config["default"][
            "enabled_programming_language"
        ]
        default_language = self.config["default"]["default_language"]
        chat = self.model.start_chat()
        response = chat.send_message(
            f"""
        You are genai Programming Language Learning Assistant.
        Your task is to undersand the question and write a code for same.

        Instructions:
        1. If programming language is not mentioned, then use {default_language} as default programming language to write a code.
        2. Strictly follow the instructions mentioned in the question.
        3. If the question is not clear then you can answer "{unable_to_understand_question}"
        4. Strictly answer the question if only {enabled_programming_language} is mentioned in question.

        If the question is about other programming language then DO NOT provide any answer, just say "{non_programming_question_error_msg}"

        """
        )

        response = chat.send_message(
            f"""{text}""", generation_config=self.genai_chat_parameters
        )
        if response.to_dict()["candidates"][0]["finish_reason"] != 1:
            self.logger.info(
                "ask_codey: No response from QnA due to LLM safety checks."
            )
            self.logger.info("LLM error code: %s\n", response.raw_prediction_response)
        response = response.text
        response = response.replace("```", "\n\n```")
        response = response.replace("```java", "``` java")
        return response

    def get_programming_lanuage_from_query(
        self, text: str, enabled_programming_language: List
    ) -> List[str]:
        """
        Extracts programming languages mentioned in a user's query.

        Args:
            text (str): The user's query.
            enabled_programming_language (List): List of supported languages.

        Returns:
            list: A list of programming languages extracted from the query (potentially empty).
        """

        response = self.model.generate_content(
            f"""
            You are strict programming languages extractor.

            Instructions:
            1. Extract only programming languages from message.
            2. Don't return any other languages other than programming.
            3. return [] if no programming lanuage in mentioned in message.
            4. {enabled_programming_language} these are the programming languages.

            Examples:
            write a code for fibonacci series in C++? : ["C++"]
            write a code using C# to generate palindrome series : ["C#"]
            using python, write a sample application code to create endpoint? : ["Python"]
            what are classes in Java? : ["Java"]
            write a code for reverse a string : []
            what are data types? : []

            What are the programming languages mentioned in below message?
            MESSAGE:{text}
            programming languages:""",  # pylint: disable=C0301:line-too-long
            generation_config=self.genai_qna_parameters,
        )

        programming_lang = response.text
        program_lang_in_query = []
        if programming_lang:
            try:
                programming_lang = programming_lang.replace("'", '"')
                programming_lang = json.loads(programming_lang)
                program_lang_in_query = [
                    x.lower().replace(" ", "").strip() for x in programming_lang
                ]
            except Exception:  # pylint: disable=W0718,W0703
                self.logger.info("Error while extracting programming language.")
        return program_lang_in_query

    def check_programming_language_in_query(
        self, text: str
    ) -> tuple[List[str], set[str]]:
        """
        Identifies supported programming languages mentioned in a user's query.

        Args:
            text (str): The user's query.

        Returns:
            tuple:
                * list: All programming languages found in the query.
                * set: Programming languages in the query that are supported by the assistant.
        """

        enabled_programming_language = self.config["default"][
            "enabled_programming_language"
        ]
        enabled_programming_language_list = enabled_programming_language.split(",")
        enabled_programming_language_list = [
            x.lower().replace(" ", "").strip()
            for x in enabled_programming_language_list
        ]
        program_lang_in_query = self.get_programming_lanuage_from_query(
            text, enabled_programming_language_list
        )
        allowed_language_in_query = set(enabled_programming_language_list).intersection(
            set(program_lang_in_query)
        )

        return program_lang_in_query, allowed_language_in_query

    def classify_intent(self, text: str, session_state: str) -> tuple[str, str]:
        """
        Orchestrates intent classification, response generation, and error handling.

        Handles the following intents:
            * 'WELCOME'
            * 'WRITE_CODE'
            * 'PROGRAMMING_QUESTION_AND_ANSWER'
            * 'FOLLOWUP'
            * 'CLOSE'
            * 'OTHER'

        Args:
            text (str): User's message.
            session_state (str): Unique ID for tracking the conversation.

        Returns:
            tuple:
                * str: Response to the user's message.
                * str: Classified intent.
        """

        try:
            response = ""

            intent = self.genai_classify_intent(text)
            self.logger.info("Classified intent: %s", intent)

            if intent == "WELCOME":
                response = self.greetings(text)
            elif intent == "WRITE_CODE":
                (
                    program_lang_in_query,
                    allowed_language_in_query,
                ) = self.check_programming_language_in_query(text)
                self.logger.info("program_lang_in_query: %s", program_lang_in_query)
                self.logger.info(
                    "allowed_language_in_query: %s", allowed_language_in_query
                )
                if (
                    len(program_lang_in_query) > 0
                    and len(allowed_language_in_query) == 0
                ):
                    response = self.config["error_msg"][
                        "non_programming_question_error_msg"
                    ]
                else:
                    response = self.ask_codey(text)
            elif intent == "PROGRAMMING_QUESTION_AND_ANSWER":
                if self.index_endpoint and self.deployed_index_id:
                    input_token_len = self.model.count_tokens(text).total_tokens
                    self.logger.info("Input_token_len for QnA: %s", input_token_len)

                    qna_answer = self.genai_qna.ask_qna(text)

                    if qna_answer:
                        response = qna_answer
                    else:
                        self.logger.info("Asking codey when no answer from QnA")
                        response = self.ask_codey(text)
                else:
                    self.logger.info(
                        "Asking codey as Index or Endpoint is not available"
                    )
                    response = self.ask_codey(text)
            elif intent == "FOLLOWUP":
                response = self.ask_codey(text + " based on previous message")
            elif intent == "CLOSE":
                response = self.closing(text)
            else:
                response = self.config["error_msg"]["other_intent_error_msg"]
        except Exception as e:  # pylint: disable=W0718,W0703,C0103
            self.logger.error("Session : %s", session_state)
            self.logger.error("Error : %s", e)

            return (
                "We're sorry, but we encountered a problem. Please try again.",
                "ERROR",
            )
        return (response, intent)
