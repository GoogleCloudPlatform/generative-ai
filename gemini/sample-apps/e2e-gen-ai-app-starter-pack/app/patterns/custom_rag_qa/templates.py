from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)

template_docs = PromptTemplate.from_template(
    """## Context provided:
{% for doc in docs%}
<Document {{ loop.index0 }}>
{{ doc.page_content | safe }}
</Document {{ loop.index0 }}>
{% endfor %}
""",
    template_format="jinja2",
)

inspect_conversation_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an AI assistant tasked with analyzing the conversation "
and determining the best course of action.""",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

rag_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an AI assistant for question-answering tasks. 

Answer to the best of your ability using the context provided. 
If you're unsure, it's better to acknowledge limitations than to speculate.
""",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
