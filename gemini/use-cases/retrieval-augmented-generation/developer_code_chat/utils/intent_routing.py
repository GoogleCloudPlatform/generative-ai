# Copyright 2023 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Generative AI Models based functions to respond questions"""
# Imports
import configparser
import copy
import logging
import json
from vertexai.preview.language_models import ChatMessage
from vertexai.generative_models import GenerativeModel, GenerationConfig

class IntentRouting:
    """genai Assistant"""

    def __init__(
        self, config_file: str = "config.ini", logger=logging.getLogger()
    ) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.logger = logger
        
        # self.genai_qna_parameters = {
        #     "temperature": float(
        #         self.config["genai_qna"]["temperature"]
        #     ),
        #     "max_output_tokens": int(
        #         self.config["genai_qna"]\
        #           ["max_output_tokens"]
        #     ),
        #     "top_p": float(\
        #       self.config["genai_qna"]["top_p"]),
        #     "top_k": int(self.config["genai_qna"]["top_k"]),
        # }
        # self.genai_chat_parameters = {
        #     "temperature": float(
        #         self.config["genai_chat"]["temperature"]
        #     ),
        #     "max_output_tokens": int(
        #         self.config["genai_chat"]["max_output_tokens"]
        #     ),
        # }
        self.genai_qna_parameters = GenerationConfig(
            temperature = float(self.config["genai_qna"]["temperature"]),
            max_output_tokens = int(self.config["genai_qna"]["max_output_tokens"]),
            top_p = float(self.config["genai_qna"]["top_p"]),
            top_k = int(self.config["genai_qna"]["top_k"])
        )
        self.genai_chat_parameters = GenerationConfig(
            temperature = float(self.config["genai_chat"]["temperature"]),
            max_output_tokens = int(self.config["genai_chat"]["max_output_tokens"])
        )

    def get_chat_user_history(self, chat_history):
        """Get Chat User History"""
        if chat_history:
            message_list = []    
            for chat_msg in chat_history[-1:]:  # last user message
                # print(chat_msg)
                if chat_msg[0] and len(chat_msg[0]):
                    message_list.append(chat_msg[0])
            if len(message_list) == 0:
                return None
            return message_list
        return None

    def get_chat_history(self, chat_history):
        """Get Chat History"""
        if chat_history:
            message_list = []
            for chat_msg in chat_history[-3:]:
                # print(chat_msg)
                if chat_msg[0] and len(chat_msg[0]):
                    message_list.append(
                        ChatMessage(content=str(chat_msg[0]), author="user")
                    )
                if chat_msg[0] and len(chat_msg[1]):
                    # remove references from chat history.
                    chat_msg = chat_msg[1].split("Reference:")[0]
                    message_list.append(ChatMessage(content=str(chat_msg), \
                      author="bot"))
            if len(message_list) == 0:
                return None
            return message_list
        return None

    def other_intent(self, text, chat_model, chat_history):
        """Respond for Other type of Intent"""
        chat_history = self.get_chat_history(chat_history)
        chat = chat_model.start_chat(
            # history=chat_history
        )
        response = chat.send_message(f"""{text}""", generation_config=self.genai_chat_parameters)
        message = response.text
        return message

    def greetings(self, chat_model, chat_history, text):
        """Respond for Greetings or Welcome Intent"""
        enabled_programming_language = self.config["default"][
            "enabled_programming_language"
        ].split(",")
        enabled_programming_language = ", ".join(
            [lang.title() for lang in enabled_programming_language]
        )
        enabled_qna_programming_language = self.config["default"][
            "enabled_qna_programming_language"
        ].split(",")
        enabled_qna_programming_language = ", ".join(
            [lang.title() for lang in enabled_qna_programming_language]
        )
        chat_history = self.get_chat_history(chat_history)
        
        chat = chat_model.start_chat(history=chat_history)
        response = chat.send_message(
            f"""You are Generative AI powered genai Learning Assistant.

        You are trained ONLY to answers questions related to following programming languages: {enabled_programming_language}

        Write a brief greeting message:"""
        )
        # parameters_local = copy.deepcopy(self.genai_chat_parameters)
        # parameters_local["temperature"] = 1
        parameters_local = GenerationConfig(
            temperature = 0.7,
            max_output_tokens = int(self.config["genai_chat"]["max_output_tokens"])
        )
        
        response = chat.send_message(f"""{text}""", generation_config=parameters_local)
        message = response.text
        return message

    def closing(self, chat_model, chat_history, text):
        """Respond for Closing Intent"""
        parameters_local = GenerationConfig(
            temperature = 0.7,
            max_output_tokens = int(self.config["genai_chat"]["max_output_tokens"])
        )
        chat_history = self.get_chat_history(chat_history)
        chat = chat_model.start_chat()#history=chat_history)
        response = chat.send_message(
            """You are Generative AI powered genai Learning Assistant.
                Write a brief closing thank you message:"""
        )
        response = chat.send_message(f"""{text}""", generation_config=parameters_local)
        message = response.text
        return message

    def elaborate_qna(self, text, chat_model, chat_history, question):
        """Explain the answer of a question in detail."""
        chat_history = self.get_chat_history(chat_history)
        chat = chat_model.start_chat()#history=chat_history)
        response = chat.send_message(
            """
        You are genai Programming Language Learning Assistant. Your task is to explain following text in detail:

        Instructions:
            1. Think step-by-step and then answer.
            2. Try to explain answers in detail to explain students.)"""
        )
        response = chat.send_message(
            f"""Explain following context in detail:
        Context : {text}
        Question : {question}
        Explanation : """,
            generation_config=self.genai_chat_parameters,
        )
        detailed_answer = response.text
        if "not able to help with that" in detailed_answer:
            return text
        return detailed_answer

    def genai_classify_intent(self, text, model):
        """Classify the intent of incoming message"""
        # response = model.predict(
        response = model.generate_content(
            f"""
            You are strict intent classifier , Classify intent of messages into 5 categories

            Instructions:
            1. Only use WELCOME , WRITE_CODE , PROGRAMMING_QUESTION_AND_ANSWER , CLOSE , OTHER , FOLLOWUP intents.
            2. Messages can be read as case-insensitive.
            3. Reply ONLY with category of intent. Don't generate extra examples.
            4. All other messages that don't belong to WRITE_CODE or PROGRAMMING_QUESTION_AND_ANSWER will be classified as OTHER

            Intents:
            1. WELCOME : is the category with greeting message and to know about the assistant for example hi, hey there, Hello, Good morning, good afternoon, good evening, who are you?, what prgramming languesges do you know?, what do you do?, how can you help me?.
            2. WRITE_CODE : is the category with code writing , debugging, explain code message. user wants you to write a code.
            3. PROGRAMMING_QUESTION_AND_ANSWER: is the category with strictly programming language related descriptive or theoretical questions. Any other question non related to programming should go into others.
            4. CLOSE : is the category for closing the chat with messages like okay THANKS!, bye, Thanks, thank you, goodbye.
            5. OTHER : is the category where user is asking non information technology related quesiontion. for example Who is PM of india, what happended in G20 summit.
            6. FOLLOWUP : is the category with user is asking the followup question, such as write a code for same , give me the code for above, give me example, explain in detail, what above method is doing.

            Strictly If you do not know the answer, classify as OTHER.

            What is the intent of the below message?
            MESSAGE:{text}
            INTENT:"""  # pylint: disable=C0301:line-too-long
            , generation_config=self.genai_qna_parameters
        )
        
        # if response.is_blocked:
        if response.to_dict()['candidates'][0]["finish_reason"]!=1:
            self.logger.info(\
              "classify_intent: No response from QnA due to LLM safety checks.")
            self.logger.info("LLM error code: %s\n", \
              response.raw_prediction_response)

        intent = response.text
        return str(intent).strip()

    def ask_question_and_answer_codey(self, text, chat_model, chat_history):
        """Respond question and answer related questions."""
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
        chat_history = self.get_chat_history(chat_history)
        # print("chat_history", chat_history)
        
        chat = chat_model.start_chat()#history=chat_history)
        response = chat.send_message(
            f"""
        You are genai Programming Language Learning Assistant.
        Your task is to undersand the question and answer descriptive answer for the same.

        Instructions:
        1. If programming language is not mentioned, then use {default_language} as default programming language to write a code.
        2. Strictly follow the instructions mentioned in the question.
        3. If the question is not clear then you can answer "{unable_to_understand_question}"
        4. Strictly answer the question if only {enabled_programming_language} is mentioned in question.

        If the question is about other programming language then DO NOT provide any answer, just say "{non_programming_question_error_msg}"
        """)

        response = chat.send_message(f"""{text}""", generation_config=self.genai_chat_parameters)
        # if response.is_blocked:
        if response.to_dict()['candidates'][0]["finish_reason"] != 1:
            self.logger.info(\
              "ask_codey: No response from QnA due to LLM safety checks.")
            self.logger.info("LLM error code: %s\n", \
              response.raw_prediction_response)
        response = response.text
        response = response.replace("```", "\n\n```")
        response = response.replace("```java", "``` java")
        return response

    def ask_codey(self, text, chat_model, chat_history):
        """Respond code related questions."""
        chat_history = self.get_chat_history(chat_history)
        print("------------")
        print("chat history")
        print(chat_history)
        print("------------")
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
        chat = chat_model.start_chat()#history=chat_history)
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

        """)

        response = chat.send_message(f"""{text}""", generation_config=self.genai_chat_parameters)
        # if response.is_blocked:
        if response.to_dict()['candidates'][0]["finish_reason"] != 1:
            self.logger.info(\
              "ask_codey: No response from QnA due to LLM safety checks.")
            self.logger.info("LLM error code: %s\n", \
              response.raw_prediction_response)
        response = response.text
        response = response.replace("```", "\n\n```")
        response = response.replace("```java", "``` java")
        return response

    def get_programming_lanuage_from_query(
        self, model, text, enabled_programming_language
    ):
        """Extract Programming lanuages of incoming message"""
        # response = model.predict(
        response = model.generate_content(
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
            programming languages:"""  # pylint: disable=C0301:line-too-long
            , generation_config=self.genai_qna_parameters
        )
        
        programming_lang = response.text
        program_lang_in_query = []
        if programming_lang:
            try:
                programming_lang = programming_lang.replace("'", '"')
                # print(programming_lang)
                programming_lang = json.loads(programming_lang)
                program_lang_in_query = [
                    x.lower().replace(" ", "").strip() for x in programming_lang
                ]
            except Exception:  # pylint: disable=W0718,W0703
                self.logger.info("Error while extracting programming language.")
        return program_lang_in_query

    def check_programming_language_in_query(self, model, text, intent):
        """Check if which programming language is mentioned in the use query"""
        if intent == "WRITE_CODE":
            enabled_programming_language = self.config["default"][
                "enabled_programming_language"
            ]
        else:
            enabled_programming_language = self.config["default"][
                "enabled_qna_programming_language"
            ]
        enabled_programming_language = enabled_programming_language.split(",")
        enabled_programming_language_list = [
            x.lower().replace(" ", "").strip() \
              for x in enabled_programming_language
        ]
        program_lang_in_query = self.get_programming_lanuage_from_query(
            model, text, enabled_programming_language
        )
        allowed_language_in_query = set(enabled_programming_language_list).\
          intersection(set(program_lang_in_query))

        return program_lang_in_query, allowed_language_in_query

    def classify_intent(
        self, text, session_state, model, chat_model, chat_history, genai_qna
    ):
        """Classify intent of incoming query"""
        try:
            response = ""
            answer_reference = ""

            intent = self.genai_classify_intent(text, model)
            self.logger.info("Classified intent: %s", intent)
            if intent == "WELCOME":
                response = self.greetings(chat_model, chat_history, text)
            elif intent == "WRITE_CODE":
                (
                    program_lang_in_query,
                    allowed_language_in_query,
                )=self.check_programming_language_in_query(model, text, intent)
                self.logger.info("program_lang_in_query: %s", \
                  program_lang_in_query)
                self.logger.info("allowed_language_in_query: %s", \
                  allowed_language_in_query)
                if (
                    len(program_lang_in_query) > 0
                    and len(allowed_language_in_query) == 0
                ):
                    response = self.config["error_msg"][
                        "non_programming_question_error_msg"
                    ]
                else:
                    response = self.ask_codey(text, chat_model, chat_history)
            elif intent == "PROGRAMMING_QUESTION_AND_ANSWER":
                (
                    program_lang_in_query,
                    allowed_language_in_query,
                ) = self.check_programming_language_in_query(model, \
                  text, intent)
                # print(f"\nprogram_lang_in_query: {program_lang_in_query}")
                # print(f"allowed_language_in_query: {allowed_language_in_query}")
                if (
                    len(program_lang_in_query) > 0
                    and len(allowed_language_in_query) == 0
                ):
                    response = self.config["error_msg"][
                        "non_qna_programming_question_error_msg"
                    ]
                else:
                    qna_answer_dict = genai_qna.ask_qna(text)
                    json_response_str = json.dumps(qna_answer_dict)

                    self.logger.info("Document Retrival : %s", \
                      json_response_str)
                    if (
                        qna_answer_dict["is_answer"] is True
                        and qna_answer_dict["answer"] != ""
                        and len(qna_answer_dict["reference_logs"]) != 0
                    ):
                        response = self.elaborate_qna(
                            qna_answer_dict["answer"], chat_model,
                            chat_history, text
                        )
                        answer_reference = "\n\n" + \
                          qna_answer_dict["answer_reference"]
                    else:
                        self.logger.info("inside codey")
                        response = self.ask_question_and_answer_codey(
                            text, chat_model, chat_history
                        )
            elif intent == "FOLLOWUP":
                response = self.ask_question_and_answer_codey(
                    text + " based on previous message",
                    chat_model, chat_history
                )
            elif intent == "CLOSE":
                response = self.closing(chat_model, chat_history, text)
            else:
                response = self.config["error_msg"]["other_intent_error_msg"]
        except Exception as e:  # pylint: disable=W0718,W0703,C0103
            self.logger.error("Session : %s", session_state)
            self.logger.error("Error : %s", e)
            
            import traceback
            print(traceback.format_exc())
            
            return (
                "We're sorry, but we encountered a problem. Please try again.",
                "ERROR",
                "",
            )
        return response, intent, answer_reference
