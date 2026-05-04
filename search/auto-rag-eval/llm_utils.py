from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Pydantic models for Structured Output


class QuestionClue(BaseModel):
    chain_of_thought: str = Field(
        ...,
        description="Reasoning for why this question is relevant and answerable based on the text.",
    )
    question: str = Field(..., description="The question itself.")


class ClueResponse(BaseModel):
    questions: list[QuestionClue]


class TargetedInfo(BaseModel):
    description: str = Field(
        ...,
        description="Concise description of the type of text that would be most relevant.",
    )
    original_question: str = Field(
        ..., description="Rephrased query as a clear and concise question."
    )
    hypothetical_example: str = Field(
        ...,
        description="Hypothetical excerpt of text that could be part of a relevant document.",
    )


class QAPair(BaseModel):
    question: str
    answer: str


class ReviewResult(BaseModel):
    decision: str = Field(..., description="APPROVED or REJECTED")
    reasoning: str = Field(..., description="Reasoning for the decision")


def get_client(project_id: str, location: str):
    return genai.Client(vertexai=True, project=project_id, location=location)


def clue_generator(
    text: str, client: genai.Client, model_name: str = "gemini-2.0-flash"
) -> ClueResponse:
    """Generate clues from text using Structured Output"""
    prompt = f"""
    Reference Text:
    {text}

    Task:
    You are a reference question creator. Imagine the provided text is a section from a comprehensive reference document. Based **solely** on the given Reference Text, formulate a set of insightful questions with corresponding reasoning. Each question must be answerable **exclusively** using the information found within the provided text. Do not use any external knowledge or information.

    Each question you generate should be:
    1. **Directly Relevant**: The question must pertain specifically to the content of the Reference Text.
    2. **Comprehensive**: The questions, as a whole, should reflect the major themes and key details present in the Reference Text.
    3. **Sound and Logical**: The questions should be well-formed, clear, and appropriate for a reference context.
    4. **Standalone**: The question should be self-contained and understandable without directly referencing the provided text.
    """

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ClueResponse,
        ),
    )
    return response.parsed


def targeted_information_seeking(
    query: str, client: genai.Client, model_name: str = "gemini-2.0-flash"
) -> TargetedInfo:
    """Generate targeted information for a query using Structured Output"""
    prompt = f"""
    You are a helpful information retrieval assistant.
    I will give you a query, and you need to perform the following three tasks:
    1. **Describe Text**: Provide a concise description of the type of text that would be most relevant for answering the query.
    2. **Original Question**: Rephrase the query as a clear and concise question.
    3. **Hypothetical Example**: Create a hypothetical excerpt (around 50-100 words) of text that could be part of a relevant document.

    Here is the query: "{query}"
    """

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TargetedInfo,
        ),
    )
    return response.parsed


def generate_qa_pair(
    context: str,
    profile: dict,
    client: genai.Client,
    model_name: str = "gemini-2.0-flash",
) -> QAPair:
    """Generate a Q&A pair based on context and profile"""
    prompt = f"""
    Context:
    {context}

    Profile:
    {profile}

    Task:
    Generate a question and answer pair based on the provided context and profile.
    The question should match the profile's type, persona, and difficulty.
    The answer must be grounded only in the provided context.
    """

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=QAPair,
        ),
    )
    return response.parsed


def review_qa_pair(
    qa_pair: QAPair,
    context: str,
    critic_type: str,
    client: genai.Client,
    model_name: str = "gemini-2.0-flash",
) -> ReviewResult:
    """Review a Q&A pair using a specific critic persona"""
    prompt = f"""
    Context:
    {context}

    Question: {qa_pair.question}
    Answer: {qa_pair.answer}

    Critic Type: {critic_type}

    Task:
    As a {critic_type} critic, review the Q&A pair for accuracy, clarity, and relevance to the context.
    Provide a decision (APPROVED or REJECTED) and reasoning.
    """

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ReviewResult,
        ),
    )
    return response.parsed
