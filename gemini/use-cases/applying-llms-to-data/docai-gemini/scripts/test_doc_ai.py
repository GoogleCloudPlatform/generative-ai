import re
from typing import Optional
import uuid

from entity_processor import DocumentAIEntityExtractor, ModelBasedEntityExtractor
from extractor import BatchDocumentExtractor, OnlineDocumentExtractor
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import InternalServerError, RetryError
from google.cloud import documentai, storage
from prompts_module import get_compare_entities_prompt, get_extract_entities_prompt
from temp_file_uploader import TempFileUploader
import vertexai
from vertexai.generative_models import GenerativeModel

# Batch processing


project_id = "project-id"
location = "us"  # Or other supported locations like 'eu'
processor_id = "processor-id"
processor_version_id = "processor-version-id"  # Optional for batch processing
# File to process
file_path = "test_file.pdf"
mime_type = "application/pdf"

gcs_output_uri = "gs://bucket-output"  # GCS URI for output
gcs_temp_uri = "gs://bucket-temp"  # GCS URI for output


# batch_extractor = BatchDocumentExtractor(
#     project_id=project_id,
#     location=location,
#     processor_id=processor_id,
#     gcs_output_uri=gcs_output_uri,
#     gcs_temp_uri=gcs_temp_uri,
#     processor_version_id=processor_version_id,  # Optional
#     timeout=600,  # Optional timeout in seconds
# )
# batch_document = batch_extractor.process_document(file_path, mime_type)
# print("Batch Processed Document:", batch_document)

online_extractor = OnlineDocumentExtractor(
    project_id=project_id,
    location=location,
    processor_id=processor_id,
    # processor_version_id=processor_version_id
)
online_document = online_extractor.process_document(file_path, mime_type)

docai_entity_extractor = DocumentAIEntityExtractor(online_document)
docai_entities = docai_entity_extractor.extract_entities()


# 2. Using ModelBasedEntityExtractor
temp_file_uploader = TempFileUploader(gcs_temp_uri)
gcs_input_uri = temp_file_uploader.upload_file(file_path)

prompt_extract = get_extract_entities_prompt()
model_extractor = ModelBasedEntityExtractor(
    "gemini-1.5-flash-001", prompt_extract, gcs_input_uri
)
gemini_entities = model_extractor.extract_entities()

temp_file_uploader.delete_file()

compare_prompt = get_compare_entities_prompt()
compare_prompt = compare_prompt.format(
    docai_output=str(docai_entities), gemini_output=str(gemini_entities)
)

model = GenerativeModel("gemini-1.5-flash-001")
docai_gemini_response_analysis = model.generate_content(compare_prompt)
print(docai_gemini_response_analysis.text)
