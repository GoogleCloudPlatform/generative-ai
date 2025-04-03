"""Cloud Function code to analyze a prospectus"""

import base64
import os

import functions_framework
from google.cloud.alloydb.connector import Connector
from langchain_core.prompts import PromptTemplate
from langchain_google_vertexai import VertexAI
import sqlalchemy


# Triggered from a message on a Cloud Pub/Sub topic.
@functions_framework.cloud_event
def analyze_prospectus(cloud_event):
    """Function to analyze prospectus"""
    # Print out the data from Pub/Sub, to prove that it worked
    ticker = base64.b64decode(cloud_event.data["message"]["data"])
    ticker = ticker.decode("utf-8")
    print(ticker)

    # Environment Vars
    region = os.environ["REGION"]
    project_id = os.environ["PROJECT_ID"]

    # AlloyDB Vars
    cluster = "alloydb-cluster"
    instance = "alloydb-instance"
    database = "ragdemos"
    table_name = "langchain_vector_store"
    user = "postgres"
    password = os.environ["ALLOYDB_PASSWORD"]

    # Setup sync connector
    connector = Connector()

    def getconn():
        conn = connector.connect(
            f"projects/{project_id}/locations/{region}/clusters/{cluster}/instances/{instance}",
            "pg8000",
            user=user,
            password=password,
            db=database,
        )
        return conn

    # create connection pool
    pool = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=getconn,
    )

    # Prep SQL statement
    sql = f"SELECT content FROM {table_name} WHERE ticker = '{ticker}' ORDER BY page, page_chunk"

    # Prep model and template
    model = VertexAI(
        model_name="gemini-2.0-flash", max_output_tokens=1024, temperature=0.0
    )
    template = """
<MISSION>
 You are an experienced financial analyst. Your mission is to create a detailed
 company financial overview for {ticker} using their latest prospectus. I will be
 sending you the prospectus a few chunks at a time. There are a total of
 {total_chunk_count} prospectus chunks, and I am sending you prospectus chunk numbers
 {first_chunk}-{last_chunk} as part of this request.
</MISSION>

<TASK>
 Use the financial overview labeled <OVERVIEW> below, and use the additional details from 
 the section labeled <ADDITIONAL_CONTEXT> below to improve the financial overview in the <OVERVIEW>. 
 Respond using less than 4000 characters, including whitespace.
</TASK>

<OVERVIEW>
{previous_overview}
</OVERVIEW>

<ADDITIONAL_CONTEXT>
{chunk_text}
</ADDITIONAL_CONTEXT>"""

    prompt = PromptTemplate.from_template(template)

    # Create overview of full document by iterating through chunks
    with pool.connect() as db_conn:
        # query database
        result = db_conn.execute(sqlalchemy.text(sql)).fetchall()

        # commit transaction (SQLAlchemy v2.X.X is commit as you go)
        db_conn.commit()

        # Iterate through results
        total_chunk_count = len(result)
        overview = ""
        chunk_text = ""
        first_chunk = 1
        last_chunk = 1

        for i in range(len(result)):
            current_chunk = i + 1
            first_chunk = min(first_chunk, current_chunk)
            last_chunk = max(last_chunk, current_chunk)

            # Add text to chunk_text until token window is full
            chunk_text = chunk_text + str(result[i].content) + " "
            if len(chunk_text) < 50000:
                continue

            # Invoke the model
            print(
                f"Adding chunks {first_chunk} through {last_chunk} out of {total_chunk_count} to {ticker} overview..."
            )
            fmt_prompt = prompt.format(
                total_chunk_count=total_chunk_count,
                first_chunk=first_chunk,
                last_chunk=last_chunk,
                previous_overview=overview,
                chunk_text=chunk_text,
                ticker=ticker,
            )

            overview = model.invoke(fmt_prompt)

            # Reset first_chunk and chunk_text values
            first_chunk = current_chunk + 1
            chunk_text = ""

    analysis = model.invoke(
        f"You are an experienced financial analyst. Write a financial analysis for ticker {ticker} that includes an Investment Rating (buy, sell, or hold), Investment Risk (high, medium, low), Target Investor (conservative, neutral, aggressive) and a two-paragraph analysis. Use the following company overview as context for the analysis: \n\n{overview}"
    )
    rating = model.invoke(
        f"Answering with only 1 word, classify ticker {ticker} as one of [BUY, SELL, HOLD] based on the following analysis: {analysis}"
    )
    rating = rating.strip()

    insert_stmt = sqlalchemy.text(
        "INSERT INTO investments (id, ticker, etf, market, rating, overview, analysis) VALUES (:id, :ticker, :etf, :market, :rating, :overview, :analysis)"
    )

    with pool.connect() as db_conn:
        max_id = db_conn.execute(
            sqlalchemy.text("SELECT MAX(id) FROM investments")
        ).fetchall()
        new_id = max_id[0][0] + 1
        print(new_id)

        # insert into database
        db_conn.execute(
            insert_stmt,
            parameters={
                "id": new_id,
                "ticker": ticker,
                "etf": False,
                "market": "US",
                "rating": rating,
                "overview": overview,
                "analysis": analysis,
            },
        )

        # commit transaction (SQLAlchemy v2.X.X is commit as you go)
        db_conn.commit()
        print("Finished insert")

    print("Closing database connection.")
    connector.close()
    print(f"Finished analyzing ticker {ticker}.")
