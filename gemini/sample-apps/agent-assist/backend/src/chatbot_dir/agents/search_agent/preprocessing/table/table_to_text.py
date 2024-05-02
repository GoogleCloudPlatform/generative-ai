"""This is a python utility file."""

# pylint: disable=all

import os

from img2table.document import PDF
from img2table.ocr import TesseractOCR
from src.chatbot_dir.agents.search_agent.preprocessing.table.process_function import (
    processTable,
)

# Function to process the PDF tables and save the extracted text to files.


def process_pdf_tables(DOCUMENT_PATH: str, POLICY_NAME: str) -> None:
    """Processes the PDF tables and saves the extracted text to files.

    Args:
        DOCUMENT_PATH (str): The path to the PDF document.
        POLICY_NAME (str): The name of the policy to which the PDF document belongs.
    """

    OUTPUT_PATH = f"data/static/table_text/{POLICY_NAME}/"

    pdf = PDF(src=DOCUMENT_PATH)

    ocr = TesseractOCR(lang="eng")

    pdf_tables = pdf.extract_tables(ocr=ocr)

    for idx, pdf_table in pdf_tables.items():
        try:
            os.makedirs(OUTPUT_PATH + str(idx))
        except OSError:
            pass
        if not pdf_table:
            continue
        for jdx, table in enumerate(pdf_table):
            table_df_string = table.df.to_string()
            table_string = processTable(table_df_string)
            print(table_string)
            with open(OUTPUT_PATH + f"{idx}/table_df_{jdx}.txt", "w") as f:
                f.write(table_df_string)

            with open(OUTPUT_PATH + f"{idx}/table_string_{jdx}.txt", "w") as f:
                f.write(table_string)
