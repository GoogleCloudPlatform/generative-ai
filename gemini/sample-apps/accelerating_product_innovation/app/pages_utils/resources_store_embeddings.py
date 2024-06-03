"""
This module provides functions for processing uploaded files, generating text
embeddings,
and managing data within the Google Cloud Storage (GCS) bucket.

This module:
    * Parses different file formats (CSV, text, Word, PDF), extracts
      text, splits it into chunks, and creates data packets.
    * Leverages `embedding_model_with_backoff` to embed text chunks.
    * Uploads processed data packets to a GCS bucket.
    * Stores embeddings alongside their associated metadata.
"""

import asyncio
import json
import logging
import os
from typing import Any

from PyPDF2 import PdfReader
import aiohttp as cloud_function_call
from app.pages_utils import insights
from app.pages_utils.embedding_model import embedding_model_with_backoff
from app.pages_utils.pages_config import GLOBAL_CFG
import docx
from dotenv import load_dotenv
from google.cloud import storage
import numpy as np
import pandas as pd
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)

# Define storage bucket
storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(GLOBAL_CFG["bucket_name"])


def get_chunks_iter(text: str, maxlength: int) -> list[str]:
    """Gets the chunks of text from a string.

    This function gets the chunks of text from a string.
    It splits the string into chunks of the specified maximum length and
    returns a list of the chunks.

    Args:
        text (str): The string to get the chunks of.
        maxlength (int): The maximum length of the chunks.

    Returns:
        list[str]: A list of the chunks of text.
    """
    start = 0
    end = 0
    final_chunk = []
    while start + maxlength < len(text) and end != -1:
        end = text.rfind(" ", start, start + maxlength + 1)
        final_chunk.append(text[start:end])
        start = end + 1
    final_chunk.append(text[start:])
    return final_chunk


def chunk_and_store_data(
    uploaded_file: UploadedFile,
    file_content: str,
) -> list:
    """Creates a data packet.

    This function creates and returns a list of chunks from the file contents.

    Args:
        uploaded_file: File like object from streamlit uploader.
        file_content (str): The contents of the file.

    Returns:
        final_data (list[Any]): A list of data packets.
    """
    # Creating a simple dictionary to store all information
    # (content and metadata) extracted from the document

    # Return if empty or invalid file is found.
    if file_content == "":
        return []

    final_data = []

    # Split file into chunks and process each chunk in parallel.
    text_chunks = get_chunks_iter(file_content, 2000)
    for chunk_number, chunk_content in enumerate(text_chunks):
        data_packet = {}
        data_packet["file_name"] = uploaded_file.name
        data_packet["chunk_number"] = str(chunk_number)
        data_packet["content"] = chunk_content

        # Append all chunks to final_data.
        final_data.append(data_packet)

    return final_data


async def add_embedding_col(pdf_data: pd.DataFrame) -> pd.DataFrame:
    """Adds an 'embedding' column to the PDF data.

    This function adds an 'embedding' column to the PDF data.
    It uses the 'apply' function to apply the 'generate_embeddings' function
    to each row of the 'content' column and returns the resulting DataFrame.

    Args:
        pdf_data (pd.DataFrame): The PDF data.
        ti (int): The task index.

    Returns:
        pd.DataFrame: The PDF data with the 'embedding' column.
    """
    # Make request data payload
    pdf_content = json.dumps({"pdf_data": pdf_data["content"].to_json()})

    async with cloud_function_call.ClientSession() as session:
        # URL for cloud function.
        url = f"""https://us-central1-{PROJECT_ID}.cloudfunctions.net/text-embedding"""

        # Call cloud function to generate embeddings with data and headers.
        async with session.post(
            url,
            data=pdf_content,
            headers=st.session_state.headers,
            verify_ssl=False,
        ) as embedding_response:
            # Process cloud function Response
            if embedding_response.status == 200:
                response = await embedding_response.text()  # Read response
                # Extract text embeddings and convert to pd.Series.
                text_embeddings = pd.Series(json.loads(response)["embedding_column"][0])
                # Add embedding column
                pdf_data["embedding"] = text_embeddings

    return pdf_data


async def process_rows(df: pd.DataFrame, filename: str, header: list) -> pd.DataFrame:
    """Processes the rows.

    This function processes the rows.
    It iterates over the rows of the DataFrame and creates a data packet for
    each row.
    It then returns a DataFrame with the data packets.

    Args:
        df (pd.DataFrame): The DataFrame to process.
        filename (str): The name of the file.
        header (list): The header of the file.

    Returns:
        pd.DataFrame: A DataFrame with the data packets.
    """
    final_data = []
    last_index = len(df)
    for i in range(last_index):
        chunk_content = ""
        for j, head in enumerate(header):
            chunk_content += f"{head} is {df.iloc[[i], [j]].squeeze()}. "
        data_packet = {}
        data_packet["file_name"] = filename
        data_packet["chunk_number"] = str(i + 1)
        data_packet["content"] = chunk_content

        final_data.append(data_packet)
    pdf_data = pd.DataFrame.from_dict(final_data)
    return pdf_data


async def csv_processing(
    df: pd.DataFrame,
    header: list,
    embeddings_df: pd.DataFrame,
    file: str,
) -> None:
    """Processes the CSV file.

    This function processes the CSV file.
    It splits the DataFrame into chunks and processes each chunk in parallel.
    It then concatenates the results and uploads the resulting DataFrame to
    the GCS bucket.

    Args:
        df (pd.DataFrame): The DataFrame to process.
        header (list): The header of the file.
        embeddings_df (pd.DataFrame): The DataFrame with the stored embeddings.
        file (str): The name of the file.
    """
    pdf_data = pd.DataFrame()
    df_size = len(df)
    chunk_size = 100  # Default chunk size if df_size is below all thresholds
    chunk_sizes = {
        1_000_000: 100_000,
        100_000: 10_000,
        10_000: 1_000,
    }
    for threshold, size in chunk_sizes.items():
        if df_size > threshold:
            chunk_size = size

    chunks = np.array_split(df, chunk_size)

    # Parallel processing in stages
    processed_chunks = await asyncio.gather(
        *(process_rows(chunk, file, header) for _, chunk in enumerate(chunks))
    )
    typed_chunks = await asyncio.gather(
        *(
            asyncio.to_thread(
                chunk.assign(types=[type(x) for x in chunk["content"]]), chunk
            )
            for chunk in processed_chunks
        )
    )
    embedded_chunks = await asyncio.gather(
        *(add_embedding_col(chunk) for chunk in typed_chunks)
    )

    # Combine, merge, deduplicate, and upload
    pdf_data = pd.concat(embedded_chunks + [embeddings_df])
    pdf_data = pdf_data.drop_duplicates(subset="content", keep="first").reset_index(
        drop=True
    )
    bucket.blob(
        f"{st.session_state.product_category}/embeddings.json"
    ).upload_from_string(pdf_data.to_json(), "application/json")


def load_file_content(
    uploaded_file: UploadedFile,
    uploaded_file_blob: storage.Blob,
) -> Any:
    """Loads and processes the content of various file types (text, docx, pdf).

    Args:
        uploaded_file: The file to convert to data packets.
        uploaded_file_blob (optional): A Google Cloud Storage Blob object. If
        provided, the function will upload the file content to the blob.

    Returns:
        The extracted text content of the file(s) as a single string.
    """
    # Handle case if a text file has been uploaded.
    if uploaded_file.type == "text/plain":
        # Read and decode contents of the file.
        file_content = uploaded_file.read().decode("utf-8")
        file_content = file_content.replace("\n", " ")
        uploaded_file_blob.upload_from_string(
            file_content, content_type=uploaded_file.type
        )
    # Handle case when uploaded file is a document.
    elif uploaded_file.name.lower().endswith(".docx"):
        # Read and clean up contents of the document.
        doc = docx.Document(uploaded_file)
        file_content = ""
        for para in doc.paragraphs:
            file_content += para.text
        "\n".join(file_content)
        uploaded_file_blob.upload_from_string(
            file_content, content_type=uploaded_file.type
        )
    else:
        # Read and process contents of the pdf file.
        pdf_content = uploaded_file.read()
        uploaded_file_blob.upload_from_string(
            pdf_content, content_type=uploaded_file.type
        )
        # Extract pages from the pdf.
        reader = PdfReader(uploaded_file)
        num_pages = len(reader.pages)
        file_content = ""
        # Separately load text from each page of the pdf.
        for page_num in range(num_pages):
            page = reader.pages[page_num]
            pg = page.extract_text()
            file_content += pg
    return file_content


def create_and_store_embeddings(uploaded_file: UploadedFile) -> None:
    """Converts the file to data packets.

    This function converts the file to data packets.
    It checks the file type and processes the file accordingly.
    It then uploads the resulting DataFrame to the GCS bucket.

    Args:
        uploaded_file: The file to convert to data packets.
    """
    with st.spinner("Uploading files..."):
        uploaded_file_blob = bucket.blob(
            f"{st.session_state.product_category}/{uploaded_file.name}"
        )

        embeddings_df = insights.get_stored_embeddings_as_df()
        final_data = []

        # Processing for csv/text files.
        if uploaded_file.type == "text/csv":
            # Read the csv file contents.
            df = pd.read_csv(uploaded_file)
            uploaded_file_blob.upload_from_string(df.to_csv(), "text/csv")

            # Return if file is empty or contents cannot be read.
            if df.empty:
                return

            # Create a list of csv file columns.
            header = []
            for col in df.columns:
                header.append(col)

            # Create embeddings and store contents of the csv file
            # to the GCS bucket.
            with st.spinner("Processing csv...this might take some time..."):
                asyncio.run(
                    csv_processing(df, header, embeddings_df, uploaded_file.name)
                )
            return

        file_content = load_file_content(uploaded_file, uploaded_file_blob)
        # Append processed content from the page to final data.
        final_data = chunk_and_store_data(
            uploaded_file=uploaded_file,
            file_content=file_content,
        )
        if len(final_data) == 0:
            return
        # Stores the embeddings in the GCS bucket.
        with st.spinner("Storing Embeddings"):
            # Create a dataframe from final chunked data.
            pdf_data = pd.DataFrame.from_dict(final_data)
            pdf_data.reset_index(inplace=True, drop=True)

            # Add datatype column to df.
            pdf_data["types"] = [type(x) for x in pdf_data["content"]]

            # Add embedding column to df for text embeddings.
            pdf_data["embedding"] = pdf_data["content"].apply(
                lambda x: embedding_model_with_backoff([x])
            )
            pdf_data["embedding"] = pdf_data.embedding.apply(np.array)

            # Concatenate the data of newly uploaded files with that of
            # existing file embeddings
            pdf_data = pd.concat([embeddings_df, pdf_data])
            pdf_data = pdf_data.drop_duplicates(subset=["content"], keep="first")
            pdf_data.reset_index(inplace=True, drop=True)

            # Upload newly created embeddings to gcs
            bucket.blob(
                f"{st.session_state.product_category}/embeddings.json"
            ).upload_from_string(pdf_data.to_json(), "application/json")
