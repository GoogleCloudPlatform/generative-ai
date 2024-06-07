import time

from google.cloud import bigquery
import streamlit as st
from vertexai.generative_models import FunctionDeclaration, GenerativeModel, Part, Tool

BIGQUERY_DATASET_ID = "thelook_ecommerce"

list_datasets_func = FunctionDeclaration(
    name="list_datasets",
    description="Get a list of datasets that will help answer the user's question",
    parameters={
        "type": "object",
        "properties": {},
    },
)

list_tables_func = FunctionDeclaration(
    name="list_tables",
    description="List tables in a dataset that will help answer the user's question",
    parameters={
        "type": "object",
        "properties": {
            "dataset_id": {
                "type": "string",
                "description": "Dataset ID to fetch tables from.",
            }
        },
        "required": [
            "dataset_id",
        ],
    },
)

get_table_func = FunctionDeclaration(
    name="get_table",
    description="""Get information about a table, including the description,
    schema, and number of rows that will help answer the user's question. Always
    use the fully qualified dataset and table names.""",
    parameters={
        "type": "object",
        "properties": {
            "table_id": {
                "type": "string",
                "description": "Fully qualified ID of the table to get information about",
            }
        },
        "required": [
            "table_id",
        ],
    },
)

sql_query_func = FunctionDeclaration(
    name="sql_query",
    description="Get information from data in BigQuery using SQL queries",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": """SQL query on a single line that will help give
                quantitative answers to the user's question when run on a
                BigQuery dataset and table. In the SQL query, always use the
                fully qualified dataset and table names.""",
            }
        },
        "required": [
            "query",
        ],
    },
)

sql_query_tool = Tool(
    function_declarations=[
        list_datasets_func,
        list_tables_func,
        get_table_func,
        sql_query_func,
    ],
)

model = GenerativeModel(
    "gemini-1.5-pro-001",
    generation_config={"temperature": 0},
    tools=[sql_query_tool],
)

st.set_page_config(
    page_title="SQL Talk with BigQuery",
    page_icon="vertex-ai.png",
    layout="wide",
)

col1, col2 = st.columns([8, 1])
with col1:
    st.title("SQL Talk with BigQuery")
with col2:
    st.image("vertex-ai.png")

st.subheader("Powered by Function Calling in Gemini")

st.markdown(
    """[Source Code](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/function-calling/sql-talk-app/)
    •
    [Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/multimodal/function-calling)
    •
    [Codelab](https://codelabs.developers.google.com/codelabs/gemini-function-calling)
    •
    [Sample Notebook](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/intro_function_calling.ipynb)"""
) # noqa: C0301

with st.expander("Sample prompts", expanded=True):
    st.write(
        """
        - What kind of information is in this database?
        - What percentage of orders are returned?
        - How is inventory distributed across our regional distribution centers?
        - Do customers typically place more than one order?
        - Which product categories have the highest profit margins?
    """
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"].replace("$", "\$"))  # noqa: W605, W1401
        try:
            with st.expander("Function calls, parameters, and responses"):
                st.markdown(message["BACKEND_DETAILS"])
        except KeyError:
            pass

if prompt := st.chat_input("Ask me about information in the database..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        FULL_RESPONSE = ""
        chat = model.start_chat()
        client = bigquery.Client()

        prompt += """
            Please give a concise, high-level summary followed by detail in
            plain language about where the information in your response is
            coming from in the database. Only use information that you learn
            from BigQuery, do not make up information.
            """

        response = chat.send_message(prompt)
        response = response.candidates[0].content.parts[0]

        print(response)

        api_requests_and_responses = []
        BACKEND_DETAILS = ""

        FUNCTION_CALLING_IN_PROCESS = True
        while FUNCTION_CALLING_IN_PROCESS:
            try:
                params = {}
                for key, value in response.function_call.args.items():
                    params[key] = value

                print(response.function_call.name)
                print(params)

                if response.function_call.name == "list_datasets":
                    API_RESPONSE = client.list_datasets()
                    API_RESPONSE = BIGQUERY_DATASET_ID
                    api_requests_and_responses.append(
                        [response.function_call.name, params, API_RESPONSE]
                    )

                if response.function_call.name == "list_tables":
                    API_RESPONSE = client.list_tables(params["dataset_id"])
                    API_RESPONSE = str([table.table_id for table in API_RESPONSE])
                    api_requests_and_responses.append(
                        [response.function_call.name, params, API_RESPONSE]
                    )

                if response.function_call.name == "get_table":
                    API_RESPONSE = client.get_table(params["table_id"])
                    API_RESPONSE = API_RESPONSE.to_api_repr()
                    api_requests_and_responses.append(
                        [
                            response.function_call.name,
                            params,
                            [
                                str(API_RESPONSE.get("description", "")),
                                str(
                                    [
                                        column["name"]
                                        for column in API_RESPONSE["schema"]["fields"]
                                    ]
                                ),
                            ],
                        ]
                    )
                    API_RESPONSE = str(API_RESPONSE)

                if response.function_call.name == "sql_query":
                    job_config = bigquery.QueryJobConfig(
                        maximum_bytes_billed=100000000
                    )  # Data limit per query job
                    try:
                        cleaned_query = (
                            params["query"]
                            .replace("\\n", " ")
                            .replace("\n", "")
                            .replace("\\", "")
                        )
                        query_job = client.query(cleaned_query, job_config=job_config)
                        API_RESPONSE = query_job.result()
                        API_RESPONSE = str([dict(row) for row in API_RESPONSE])
                        API_RESPONSE = API_RESPONSE.replace("\\", "").replace("\n", "")
                        api_requests_and_responses.append(
                            [response.function_call.name, params, API_RESPONSE]
                        )
                    except Exception as e:
                        API_RESPONSE = f"{str(e)}"
                        api_requests_and_responses.append(
                            [response.function_call.name, params, API_RESPONSE]
                        )

                print(API_RESPONSE)

                response = chat.send_message(
                    Part.from_function_response(
                        name=response.function_call.name,
                        response={
                            "content": API_RESPONSE,
                        },
                    ),
                )
                response = response.candidates[0].content.parts[0]

                BACKEND_DETAILS += "- Function call:\n"
                BACKEND_DETAILS += (
                    "   - Function name: ```"
                    + str(api_requests_and_responses[-1][0])
                    + "```"
                )
                BACKEND_DETAILS += "\n\n"
                BACKEND_DETAILS += (
                    "   - Function parameters: ```"
                    + str(api_requests_and_responses[-1][1])
                    + "```"
                )
                BACKEND_DETAILS += "\n\n"
                BACKEND_DETAILS += (
                    "   - API response: ```"
                    + str(api_requests_and_responses[-1][2])
                    + "```"
                )
                BACKEND_DETAILS += "\n\n"
                with message_placeholder.container():
                    st.markdown(BACKEND_DETAILS)

            except AttributeError:
                FUNCTION_CALLING_IN_PROCESS = False

        time.sleep(3)

        FULL_RESPONSE = response.text
        with message_placeholder.container():
            st.markdown(FULL_RESPONSE.replace("$", "\$"))  # noqa: W605, W1401
            with st.expander("Function calls, parameters, and responses:"):
                st.markdown(BACKEND_DETAILS)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": FULL_RESPONSE,
                "BACKEND_DETAILS": BACKEND_DETAILS,
            }
        )
