# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from data_processing_pipeline.components import ingest_data_in_datastore, process_data
from kfp import dsl


@dsl.pipeline(description="A pipeline to run ingestion of new data into the datastore")
def pipeline(
    project_id: str,
    region_vertex_ai_search: str,
    data_store_id: str,
    embedding_model: str = "text-embedding-004",
    pdf_url: str = "https://services.google.com/fh/files/misc/practitioners_guide_to_mlops_whitepaper.pdf",
) -> None:
    """Processes a PDF document and ingests it into Vertex AI Search datastore."""

    # Process the PDF document and generate embeddings
    processed_data = process_data(embedding_model=embedding_model, pdf_url=pdf_url)

    # Ingest the processed data into Vertex AI Search datastore
    ingest_data_in_datastore(
        project_id=project_id,
        region_vertex_ai_search=region_vertex_ai_search,
        input_files=processed_data.output,
        data_store_id=data_store_id,
    )
