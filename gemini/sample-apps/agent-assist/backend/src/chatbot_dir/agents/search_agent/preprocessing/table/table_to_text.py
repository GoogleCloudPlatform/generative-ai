"""This is a python utility file."""

# pylint: disable=E0401

import os

from img2table.document import PDF
from img2table.ocr import TesseractOCR
from src.chatbot_dir.agents.search_agent.preprocessing.table.process_function import (
    process_table,
)

# Function to process the PDF tables and save the extracted text to files.


def process_pdf_tables(document_path: str, policy_name: str) -> None:
    """Processes the PDF tables and saves the extracted text to files.

    Args:
        document_path (str): The path to the PDF document.
        policy_name (str): The name of the policy to which the PDF document belongs.
    """

    output_path = f"data/static/table_text/{policy_name}/"

    pdf = PDF(src=document_path)

    ocr = TesseractOCR(lang="eng")

    pdf_tables = pdf.extract_tables(ocr=ocr)

    for idx, pdf_table in pdf_tables.items():
        try:
            os.makedirs(output_path + str(idx))
        except OSError:
            pass
        if not pdf_table:
            continue
        for jdx, table in enumerate(pdf_table):
            table_df_string = table.df.to_string()
            table_string = process_table(table_df_string)
            print(table_string)
            with open(
                output_path + f"{idx}/table_df_{jdx}.txt", "w", encoding="UTF-8"
            ) as f:
                f.write(table_df_string)

            with open(
                output_path + f"{idx}/table_string_{jdx}.txt", "w", encoding="UTF-8"
            ) as f:
                f.write(table_string)
