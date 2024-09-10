QA_EXTRACTION_PROMPT = """\
Here is the context:
{context_str}

Given the contextual information, \
generate {num_questions} questions this context can provide \
specific answers to which are unlikely to be found elsewhere.

Higher-level summaries of surrounding context may be provided \
as well. Try using these summaries to generate better questions \
that this context can answer.

"""

QA_PARSER_PROMPT = """Parse the following list of questions:\
      {questions_list}"""
