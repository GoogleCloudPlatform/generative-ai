"""Prompt management class"""

from dataclasses import asdict, dataclass, field

SYSTEM_PROMPT = "You are an expert assistant specializing in \
    financial products and services. Your primary goal is to help users\
          understand Google's financial offerings, guidelines, and processes.\
        You will answer questions about different financial topics \
            (e.g., investments, loans, savings, retirement planning) \
            and any relevant industry regulations surrounding these topics."

QA_PROMPT_TMPL = (
    "Context information is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Please be concise and only answer the question given the above context. \
        Your answer should include all relevant \
            scenarios if the question is generic.\n"
    "If these are present you will need to extract \
        the relevant info from the table(s) present.\n"
    "Ensure that the answer includes the proper rows \
        from the markdown table(s) in order to answer the question. \
        Your answer may be contained within\
            multiple tables so do not ignore them all.\n"
    "Think step by step in coming up with your answer \
        and keep your answer short and concise.\n"
    "Query: {query_str}\n"
    "Answer: "
)

REFINE_PROMPT_TMPL = (
    "The original query is as follows: {query_str}\n"
    "We have provided an existing answer: {existing_answer}\n"
    "We have the opportunity to refine the existing answer "
    "(only if needed) with some more context below.\n"
    "------------\n"
    "{context_msg}\n"
    "------------\n"
    "Given the new context, refine the \
        original answer to be more thorough and complete. \n."
    "Ensure that the answer includes the proper rows \
        from the markdown table in order to answer the question.\n"
    "If the context isn't useful, return the \
        original answer or say you don't know. Just answer the question,\
              do not include 'Refined Answer:'. \
                Think step by step in coming up with \
                    your answer and keep the answer short and concise\n"
    "Refined Answer: "
)


HYDE_PROMPT_TMPL = (
    "Please answer the below question using your \
        expert knowledge of [DOMAIN-SPECIFIC TOPICS] and any relevant \
            industry regulations surrounding these topics. \n"
    "Your answer should include \
        all relevant scenarios if the question is generic. \n"
    "Ensure the answer is comprehensive and covers all applicable scenarios.\n"
    "{context_str}\n"
)

TREE_SUMMARIZE_PROMPT_TMPL = (
    "Context information from multiple sources is below. Each source may or"
    " may not have \na relevance score attached to"
    " it.\n---------------------\n{context_str}\n---------------------\nGiven"
    " the information from multiple sources and their associated relevance"
    " scores (if provided) and not prior knowledge, answer the question. If"
    " the answer is not in the context, inform the user that you can't answer"
    " the question.\nQuestion: {query_str}\nAnswer: "
)

MULTI_SELECT_PROMPT_TMPL = (
    "Some choices are given below. It is provided in a numbered "
    "list (1 to {num_choices}), "
    "where each item in the list corresponds to a particular \
        set of documents you can use to answer the question.\n"
    "---------------------\n"
    "{context_list}"
    "\n---------------------\n"
    "Using these choices"
    "(no more than {max_outputs}, but only select what is needed) that "
    "are most relevant to the question: '{query_str}'\n"
)

CHOICE_SELECT_PROMPT_TMPL = (
    "A list of documents is shown below. Each document has a \
        number next to it along "
    "with a summary of the document. A question is also provided. \n"
    "Respond with the numbers of the documents "
    "you should consult to answer the question, \
        in order of relevance, as well\n"
    "as the relevance score. \
        The relevance score is a number from 1-10 based on"
    "how relevant you think the document is to the question.\n"
    "Do not include any documents that are not relevant to the question. \n"
    "Example format: \n"
    "Document 1:\n<summary of document 1>\n\n"
    "Document 2:\n<summary of document 2>\n\n"
    "...\n\n"
    "Document 10:\n<summary of document 10>\n\n"
    "Question: <question>\n"
    "Answer:\n"
    "Doc: 9, Relevance: 7\n"
    "Doc: 3, Relevance: 4\n"
    "Doc: 7, Relevance: 3\n\n"
    "Let's do this now and it is extremely important that you follow\
          the EXACT format above where 1 line of output is: \n"
    "Doc: <doc_num>, Relevance: <score>\n"
    "Do not include any extra formatting whatsoever\n"
    "Go!\n\n"
    "{context_str}\n"
    "Question: {query_str}\n"
    "Answer:\n"
)

EVAL_PROMPT_WCONTEXT_SYSTEM = (
    "You are an advanced large language model acting as an \
        evaluation tool for a search retrieval pipeline. \
            You will be provided with a question, \
                some documentation to serve as context, \
                    an LLM response, and a ground truth \
                        which represents the known source of truth \
                            or ideal answer to the question.\n"
    "Your task is to compare the LLM response to the ground truth. \
        You must perform an in-depth analysis of the LLM response\
              for an understanding of the question, \
                clarity of expression, and the overall relevance \
                    of the points made. Compare these points to the \
                        key points contained in the ground truth provided.\
                            Then examine the context provided for any \
                            additional details and facts that may be \
                                included in the LLM response.\n"
    "You must place a strong emphasis on the accuracy\
          of the facts and figures of the LLM response\
              when compared to the ground truth. \
                An incomplete answer that only states correct facts\
                      is better than an answer that contains even one\
                          piece of inaccurate or false information.\
                            Even one incorrect or inaccurate fact\
                                  or figure should completely discredit\
                                    the LLM answer as a whole, despite\
                                          other parts of \
                                            the answer being accurate.\n"
    "If the LLM response contains additional details or facts \
        when compared to the ground truth, \
            compare the additional details or facts against the \
                information contained in the context. \
                    If and only if found to be accurate based on the context, \
                        do not discredit the LLM response but mention the\
                              additional information in your feedback.  \
                                If the additional information includes \
                                any items that appear to be document \
                                citations or references indicated by \
                                guides or other alpha-numeric strings, \
                                do not detract points from the score.\n"
)

EVAL_PROMPT_WCONTEXT_USER = (
    "Assign a score on the continuous spectrum of integers from 0 to 100. \
        Supply the score at the beginning of the response, \
            leave a blank line, and then provide any other feedback. \
            It is extremely important you maintain this format of response. \
            Remember to be fair, unbiased, and thorough in your grading.\n"
    "Begin the grading process with the following question, \
    the accepted ground_truth, the llm's response, and the provided context. \
            Keep your assessment short and concise"
    "\n"
    "question: {question}\n"
    "ground truth: {ground_truth}\n"
    "context: {context}\n"
    "LLM response: {answer}\n"
    "score:"
)


@dataclass
class Prompts:
    """Prompt management class"""

    qa_prompt_tmpl: str = field(default=QA_PROMPT_TMPL)
    refine_prompt_tmpl: str = field(default=REFINE_PROMPT_TMPL)
    hyde_prompt_tmpl: str = field(default=HYDE_PROMPT_TMPL)
    choice_select_prompt_tmpl: str = field(default=CHOICE_SELECT_PROMPT_TMPL)
    system_prompt: str = field(default=SYSTEM_PROMPT)
    eval_prompt_wcontext_system: str = field(default=EVAL_PROMPT_WCONTEXT_SYSTEM)
    eval_prompt_wcontext_user: str = field(default=EVAL_PROMPT_WCONTEXT_USER)

    def update(self, prompt_name: str, new_content: str) -> None:
        """Update prompts"""
        if hasattr(self, prompt_name):
            setattr(self, prompt_name, new_content)
        else:
            raise ValueError(f"Invalid prompt name: {prompt_name}")

    def to_dict(self) -> dict[str, str]:
        """return prompts as dict"""
        return asdict(self)
