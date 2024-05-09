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

# pylint: disable=E0401

import asyncio
import json
import logging
import os
from typing import Any

from PyPDF2 import PdfReader
import aiohttp
from app.pages_utils.embedding_model import embedding_model_with_backoff
from app.pages_utils.insights import get_stored_embeddings_as_df
import docx
from dotenv import load_dotenv
from google.cloud import storage
import numpy as np
import pandas as pd
import streamlit as st
from typing import Union, List
from streamlit.runtime.uploaded_file_manager import UploadedFile

load_dotenv()


logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)


PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket("product_innovation_bucket")


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
    start = 0  # Initialize the starting index for each chunk.
    end = 0  # Initialize the ending index for each chunk.
    chunk_list = []

    # Iterate while we haven't reached the end of the text.
    while start + maxlength < len(text) and end != -1:
        # Search backwards from the potential end of the chunk for a space.
        end = text.rfind(" ", start, start + maxlength + 1)
        # If a space was found, split at the space (preserving the word)
        chunk_list.append(text[start:end])
        # Move to the start of the next chunk
        start = end + 1

    # Add the last remaining part of the text
    chunk_list.append(text[start:])
    return chunk_list


def create_data_packet(
    file_name: str,
    page_number: int,
    chunk_number: int,
    file_content: str,
) -> dict:
    """Creates a data packet.

    This function creates a data packet.
    It takes the file name, page number, chunk number, and file content as
    input and returns a dictionary with the data packet.

    Args:
        file_name (str): The name of the file.
        page_number (int): The page number of the chunk.
        chunk_number (int): The chunk number of the chunk.
        file_content (str): The content of the chunk.

    Returns:
        dict: A dictionary with the data packet.
    """
    # Creating a simple dictionary to store all information
    # (content and metadata) extracted from the document

    data_packet = {}
    data_packet["file_name"] = file_name
    data_packet["page_number"] = str(page_number)
    data_packet["chunk_number"] = str(chunk_number)
    data_packet["content"] = file_content
    return data_packet


async def add_embedding_col(pdf_data: pd.DataFrame) -> pd.DataFrame:
    """Adds an 'embedding' column to the PDF data.

    This function adds an 'embedding' column to the PDF data.

    Args:
        pdf_data (pd.DataFrame): The PDF data.
        ti (int): The task index.

    Returns:
        pd.DataFrame: The PDF data with the 'embedding' column.
    """
    # Generate request data payload
    json_data = pdf_data["content"].to_json()
    data = json.dumps({"pdf_data": json_data})
    # Generate request headers
    headers = {"Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        # URL for cloud function.
        url = f"""https://us-central1-{PROJECT_ID}.cloudfunctions.net/text-embedding"""

        # Call cloud function to generate embeddings with data and headers.
        async with session.post(
            url, data=data, headers=headers, verify_ssl=False
        ) as response:

            # Process cloud function Response
            if response.status == 200:
                response_text = await response.text()
                final_response = json.loads(response_text)
                embedding = final_response["embedding_column"]
                pdf_data["embedding"] = embedding
            else:
                logging.debug("Request failed:", await response.text())

    logging.debug("Embedding call end")

    return pdf_data


async def process_rows(
    df: pd.DataFrame, filename: str, header: list, page_num: int
) -> pd.DataFrame:
    """Processes the rows.

    This function processes the rows.
    It iterates over the rows of the DataFrame and creates a data packet for
    each row.
    It then returns a DataFrame with the data packets.

    Args:
        df (pd.DataFrame): The DataFrame to process.
        filename (str): The name of the file.
        header (list): The header of the file.
        page_num (int): The page number of the file.

    Returns:
        pd.DataFrame: A DataFrame with the data packets.
    """
    final_data = []
    last_index = len(df)
    for i in range(last_index):
        chunk_content = ""
        for j, head in enumerate(header):
            chunk_content += f"{head} is {df.iloc[[i], [j]].squeeze()}. "
        packet = create_data_packet(
            filename,
            page_number=page_num,
            chunk_number=i + 1,
            file_content=chunk_content,
        )
        final_data.append(packet)
    pdf_data = pd.read_json(final_data)
    return pdf_data


async def csv_pocessing(
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
    size_of_df = len(df)

    # Calculate the appropriate split number based on the dataframe size.
    thresholds = {
        1000000: 100000,
        100000: 10000,
        10000: 1000,
        100: 100,  # Default if size_of_df is smaller than any threshold
    }
    split_num = 100
    for threshold, split_val in sorted(thresholds.items(), reverse=True):
        if size_of_df > threshold:
            split_num = split_val
            break

    # Chunk data into arrays based on split_num
    df_split = np.array_split(df, split_num)

    # Parallely process dataframe splits
    parallel_csv_processor = []
    for i in range(split_num):
        parallel_csv_processor.append(
            asyncio.create_task(process_rows(df_split[i], file, header, i))
        )
    # Get results of row processing.
    parallel_csv_processor = await asyncio.gather(*parallel_csv_processor)

    temp_arr = []
    for i in range(split_num):
        temp_arr.append(
            asyncio.create_task(
                pdf_data.assign(
                    types=pdf_data["content"].apply(lambda x: type(x))
                )
                for pdf_data in parallel_csv_processor[i]
            )
        )
    parallel_csv_processor = temp_arr
    parallel_csv_processor = await asyncio.gather(*parallel_csv_processor)
    temp_arr = []
    for i in range(split_num):
        temp_arr.append(
            asyncio.create_task(add_embedding_col(parallel_csv_processor[i]))
        )
    parallel_csv_processor = temp_arr
    parallel_csv_processor = await asyncio.gather(*parallel_csv_processor)
    for i in range(split_num):
        pdf_data = pd.concat([parallel_csv_processor[i], pdf_data])

    pdf_data = pd.concat([embeddings_df, pdf_data])
    pdf_data = pdf_data.drop_duplicates(subset=["content"], keep="first")
    pdf_data.reset_index(inplace=True, drop=True)
    bucket.blob(
        f"{st.session_state.product_category}/embeddings.json"
    ).upload_from_string(pdf_data.to_json(), "application/json")
    return


def save_chunks_to_data_packet(
    file_content: str,
    uploaded_file: Union[UploadedFile, List[UploadedFile]],
    final_data: list[dict[str, Any]],
) -> None:
    """
    Splits file content into chunks, creates data packets, and appends
    to the final_data list.

    Args:
        file_content: The text content to split and process.
        uploaded_file: The name of the file the content is from.
        final_data: The list to which the data packets are appended.
    """
    if file_content == "":
        return
    text_chunks = get_chunks_iter(file_content, 2000)
    for chunk_number, chunk_content in enumerate(text_chunks):
        packet = create_data_packet(
            uploaded_file.name,
            page_number=int(1),
            chunk_number=chunk_number + 1,
            file_content=chunk_content,
        )
        final_data.append(packet)


def store_embeddings_to_gcs(
    final_data: list[dict[str, Any]],
    embeddings_df: pd.DataFrame,
) -> None:
    """
    Stores embeddings to Google Cloud Storage (GCS).

    Args:
        final_data: A list of dictionaries containing the new data
        to process (e.g., from PDFs).
        embeddings_df: A pandas DataFrame holding previously processed data.
    """
    with st.spinner("Storing Embeddings"):
        pdf_data = pd.read_json(final_data)
        pdf_data.reset_index(inplace=True, drop=True)
        pdf_data["types"] = pdf_data["content"].apply(lambda x: type(x))
        pdf_data["embedding"] = pdf_data["content"].apply(
            lambda x: embedding_model_with_backoff([x])
        )
        pdf_data["embedding"] = pdf_data.embedding.apply(np.array)
        pdf_data = pd.concat([embeddings_df, pdf_data])
        pdf_data = pdf_data.drop_duplicates(subset=["content"], keep="first")
        pdf_data.reset_index(inplace=True, drop=True)
        bucket.blob(
            f"{st.session_state.product_category}/embeddings.json"
        ).upload_from_string(pdf_data.to_json(), "application/json")


def convert_csv_to_data_packets(
    uploaded_file: Union[UploadedFile, List[UploadedFile]],
    uploaded_file_blob: storage.Blob,
    embeddings_df: pd.DataFrame,
) -> None:
    """
    Reads a CSV file, processes it into data packets, and uploads the processed
    data to a Google Cloud Storage bucket.

    Args:
        uploaded_file: A file like object from streamlit's uploader.
        uploaded_file_blob: The Blob object representing the CSV file in GCS.
        embeddings_df: A pandas DataFrame containing existing data (if any).
    """
    header = []
    df = pd.read_csv(uploaded_file)
    uploaded_file_blob.upload_from_string(df.to_csv(), "text/csv")
    if df.empty:
        return
    for col in df.columns:
        header.append(col)
    with st.spinner("Processing csv...this might take some time..."):
        asyncio.run(
            csv_pocessing(df, header, embeddings_df, uploaded_file.name)
        )


def convert_doc_or_text_to_data_packet(
    uploaded_file: Union[UploadedFile, List[UploadedFile]],
    uploaded_file_blob: storage.Blob,
    final_data: list[dict[str, Any]],
) -> None:
    """Converts a docx file into data packets and uploads to Google
       Cloud Storage.

    Args:
        uploaded_file: A file-like object (e.g., from Streamlit's file_uploader).
        uploaded_file_blob: The Google Cloud Storage Blob object for uploading.
        final_data: A list where the generated data packets will be appended.
    """
    file_content = ""
    if uploaded_file.type == "text/plain":
        file_content = uploaded_file.read().decode("utf-8")
        file_content = file_content.replace("\n", " ")
    elif (
        uploaded_file.type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        doc = docx.Document(uploaded_file)
        file_content = ""
        for para in doc.paragraphs:
            file_content += para.text
        "\n".join(file_content)

    uploaded_file_blob.upload_from_string(
        file_content, content_type=uploaded_file.type
    )
    save_chunks_to_data_packet(file_content, uploaded_file, final_data)


def convert_file_to_data_packets(
    uploaded_file: Union[UploadedFile, List[UploadedFile]]
) -> None:
    """Converts the file to data packets.

    This function converts the file to data packets.
    It then uploads the resulting DataFrame to the GCS bucket.

    Args:
        uploaded_file: The file to convert to data packets.
    """

    with st.spinner("Uploading files..."):
        uploaded_file_blob = bucket.blob(
            f"{st.session_state.product_category}/{uploaded_file.name}"
        )
        embeddings_df = get_stored_embeddings_as_df()

        final_data: list[Any] = []

        # If the file is a CSV file, it reads the file and uploads it to
        # the GCS bucket. It then processes the file in parallel and
        # uploads the resulting DataFrame to the GCS bucket.
        if uploaded_file.type == "text/csv":
            convert_csv_to_data_packets(
                uploaded_file, uploaded_file_blob, embeddings_df
            )
            return
        elif (
            uploaded_file.type == "text/plain"
            or uploaded_file.type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            convert_doc_or_text_to_data_packet(
                uploaded_file, uploaded_file_blob, final_data
            )

        else:
            file_content = uploaded_file.read()
            uploaded_file_blob.upload_from_string(
                file_content, content_type=uploaded_file.type
            )
            if file_content == "":
                return
            reader = PdfReader(uploaded_file)
            num_pgs = len(reader.pages)
            text = ""
            for page_num in range(num_pgs):
                page = reader.pages[page_num]
                text += page.extract_text()
                pg = page.extract_text()
                if pg:
                    save_chunks_to_data_packet(
                        file_content, uploaded_file, final_data
                    )
        # Store the embeddings in the GCS bucket.
        store_embeddings_to_gcs(final_data, embeddings_df)
