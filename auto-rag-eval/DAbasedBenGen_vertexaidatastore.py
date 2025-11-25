#!/usr/bin/env python3
"""
Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


Auto RAG Eval: A Novel Benchmark Creation Tool
Authors: Pouya Omran (pgomran@google.com), Tanya Dixit (dixittanya@google.com), Jingyi Wang (jingyiwa@google.com)
Status: Draft
Last Updated: 27 Mar 2025

README:
=======

Auto RAG Eval is an automated benchmark generation tool for evaluating Retrieval-Augmented Generation (RAG) systems.
It creates high-quality question-answer pairs from your document corpus using Google Cloud's Vertex AI.

PREREQUISITES:
--------------
1. Google Cloud Project with the following APIs enabled:
   - Vertex AI API
   - Discovery Engine API (for Vertex AI Search)
   - Cloud Storage API (if using GCS)

2. Authentication:
   - Set up Application Default Credentials (ADC):
     $ gcloud auth application-default login
   - Or use a service account key file

3. Vertex AI Search Data Store:
   - Create a data store in Vertex AI Search
   - Ingest your documents into the data store
   - Note the data store ID

ENVIRONMENT SETUP (.env file):
------------------------------
Create a .env file in the same directory as this script with the following variables:

PROJECT_ID=your-gcp-project-id          # Your Google Cloud Project ID
LOCATION=us-central1                    # GCP region for Vertex AI
DATA_STORE_ID=your-data-store-id        # Your Vertex AI Search data store ID
TOP_K_CHUNKS=3                          # Number of top chunks to retrieve (default: 3)
NEIGHBOUR_CHUNKS=0                      # Number of neighboring chunks to include (default: 0)
MAX_RETRIES=3                           # Maximum retry attempts for API calls (default: 3)
LOCAL_DIRECTORY=                        # Optional: local directory path

HOW TO RUN:
-----------
Basic usage:
$ python DAbasedBenGen_vertexaidatastore.py

With custom parameters:
$ python DAbasedBenGen_vertexaidatastore.py \
    --docs 2 \
    --chunks 2 \
    --clues 2 \
    --profiles 2 \
    --chunks-to-merge 3 \
    --output-file benchmark.json

Command-line arguments (all optional):
  --project-id        Override PROJECT_ID from .env
  --location          Override LOCATION from .env
  --data-store-id     Override DATA_STORE_ID from .env
  --docs              Number of documents to process (default: 2)
  --chunks            Number of chunks per document (default: 2)
  --clues             Number of clues per chunk (default: 2)
  --profiles          Number of Q&A profiles per clue (default: 2)
  --chunks-to-merge   Number of chunks to merge into bigger chunks (default: 3)
  --output-file       Output JSON filename (default: benchmark.json)
  --qa-profiles-file  QA profiles JSON file path (default: qa_profiles.json in script directory)
  --llm-model         LLM model to use (default: gemini-2.0-flash)
  --top-k-chunks      Number of top chunks to retrieve (default: 3)
  --neighbour-chunks  Number of neighboring chunks to include (default: 0)
  --max-retries       Maximum retry attempts for API calls (default: 3)
ARCHITECTURE OVERVIEW:
----------------------
The tool follows a multi-stage pipeline approach:

1. Document Selection:
   - Lists all documents from Vertex AI Search data store
   - Randomly selects specified number of documents

2. Chunk Processing:
   - Retrieves chunks for each selected document
   - Merges consecutive chunks into bigger chunks for context
   - Randomly selects chunks for processing

3. Clue Generation:
   - For each chunk, generates potential questions (clues)
   - Uses Gemini model to identify key topics and concepts

4. Context Retrieval:
   - For each clue, searches for relevant contexts
   - Uses Vertex AI Search to find related chunks
   - Applies relevance filtering to extract focused content

5. Q&A Profile Generation:
   - Analyzes context to suggest Q&A generation profiles
   - Profiles vary by type (How-to, Explanatory, etc.), persona, and difficulty
   - Profiles are loaded from qa_profiles.json for easy customization

6. Q&A Generation:
   - Generates question-answer pairs based on profiles
   - Ensures Q&As are self-contained and context-based

7. Review Process:
   - Multi-agent review system validates each Q&A
   - Only approved Q&As are saved to the benchmark

8. Incremental Saving:
   - Each approved Q&A is saved immediately to the output file
   - Protects against data loss from interruptions

OUTPUT FORMAT:
--------------
The tool generates a JSON file with the following structure:
[
    {
        "context": "The distilled context used for Q&A generation",
        "Q&A Gen Profile": {profile details},
        "Question": "The generated question",
        "Answer": "The generated answer"
    },
    ...
]

MONITORING:
-----------
The script provides detailed logging with [LOGGING] prefix for:
- Function entry/exit points
- Processing progress
- API call attempts and retries
- Error messages and recovery attempts

ERROR HANDLING:
---------------
- Automatic retry with exponential backoff for API failures
- Graceful degradation when individual operations fail
- Incremental saving prevents complete data loss
- Detailed error logging for troubleshooting

"""


# Imports
from google import genai
import google.generativeai as generativeai
from google.cloud import aiplatform
from google.cloud import storage
from vertexai.preview.generative_models import GenerativeModel, Tool

from typing import Optional, Sequence, List, Dict, Any
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine
from google.cloud import discoveryengine_v1 as discoveryengine_v1

import json
import re
import io
import time
import pandas as pd
from datetime import datetime
import random
import types
import os
import argparse
from dotenv import load_dotenv

from google.api_core.exceptions import InternalServerError
from google.api_core.exceptions import RetryError


# Load environment variables from .env file
load_dotenv()

# Configuration Variables from environment
PROJECT_ID = os.getenv("PROJECT_ID", "aimc-410006")
LOCATION = os.getenv("LOCATION", "us-central1")
LOCAL_DIRECTORY = os.getenv("LOCAL_DIRECTORY", "")
#TOP_K_CHUNKS = int(os.getenv("TOP_K_CHUNKS", "3"))
#NEIGHBOUR_CHUNKS  = int(os.getenv("NEIGHBOUR_CHUNKS", "0"))
#MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
TOP_K_CHUNKS = int("3")
NEIGHBOUR_CHUNKS  = int("0")
MAX_RETRIES = int("3")


# Vertex AI Search configuration
DATA_STORE_ID = os.getenv("DATA_STORE_ID", "your-data-store-id")

# Initialize clients
client = None
storage_client = None


def initialize_clients():
    """Initialize Google Cloud clients"""
    global client, storage_client
    
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    storage_client = storage.Client()
    
    # Initialize Vertex AI
    aiplatform.init(project=PROJECT_ID, location=LOCATION)


# Helper Functions

def clean_json_string(json_string):
    """Clean and format JSON string from model response"""
    lines = json_string.text.split('\n')
    json_string = '\n'.join(lines[1:-1])
    json_string = json_string.strip()
    json_string = json_string.replace('"', '"').replace('"', '"')
    json_string = json_string.strip().strip('`')
    json_string = json_string.replace('\r\n', '\n').replace('\r', '\n')
    return json_string


def convert_list_to_json(benchmark_list, json_file_path):
    """Convert benchmark list to JSON format and save to file"""
    json_data = []
    for i, item in enumerate(benchmark_list):
        if isinstance(item, dict):
            new_item = {}
            if 'distilled context:' in item:
                new_item['context'] = convert_to_serializable(item['distilled context:'])
            if 'qa gen profile:' in item:
                new_item['Q&A Gen Profile'] = convert_to_serializable(item['qa gen profile:'])
            
            if 'qa:' in item and isinstance(item['qa:'], dict):
                qa_data = item['qa:']
                if 'question' in qa_data and isinstance(qa_data['question'], dict) and 'question' in qa_data['question']:
                    new_item['Question'] = convert_to_serializable(qa_data['question']['question'])
                if 'answer' in qa_data and isinstance(qa_data['answer'], dict) and 'answer' in qa_data['answer']:
                    new_item['Answer'] = convert_to_serializable(qa_data['answer']['answer'])
            if len(new_item) > 0:
                json_data.append(new_item)
        else:
            print(f"Warning: Element at index {i} is not a dictionary.")
            continue

    try:
        with open(json_file_path, 'w') as f:
            json.dump(json_data, f, indent=4)
            return json_data
    except Exception as e:
        print(f"Error writing to JSON file: {e}")


def convert_to_serializable(obj):
    """Recursively converts an object to a JSON-serializable representation"""
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, types.MappingProxyType):
        return convert_to_serializable(dict(obj))
    elif hasattr(obj, '__dict__'):
        return convert_to_serializable(obj.__dict__)
    else:
        return obj


def save_qa_incrementally(benchmark_entry, output_file):
    """Save a single Q&A entry incrementally to the output file"""
    try:
        # Convert the benchmark entry to the format used by convert_list_to_json
        formatted_entry = {}
        if 'distilled context:' in benchmark_entry:
            formatted_entry['context'] = convert_to_serializable(benchmark_entry['distilled context:'])
        if 'qa gen profile:' in benchmark_entry:
            formatted_entry['Q&A Gen Profile'] = convert_to_serializable(benchmark_entry['qa gen profile:'])
        
        if 'qa:' in benchmark_entry and isinstance(benchmark_entry['qa:'], dict):
            qa_data = benchmark_entry['qa:']
            if 'question' in qa_data and isinstance(qa_data['question'], dict) and 'question' in qa_data['question']:
                formatted_entry['Question'] = convert_to_serializable(qa_data['question']['question'])
            if 'answer' in qa_data and isinstance(qa_data['answer'], dict) and 'answer' in qa_data['answer']:
                formatted_entry['Answer'] = convert_to_serializable(qa_data['answer']['answer'])
        
        # Read existing data
        with open(output_file, 'r') as f:
            existing_data = json.load(f)
        
        # Append new entry
        existing_data.append(formatted_entry)
        
        # Write back
        with open(output_file, 'w') as f:
            json.dump(existing_data, f, indent=4)
        
        print(f"[LOGGING] Successfully saved Q&A #{len(existing_data)} to {output_file}")
        return True
        
    except Exception as e:
        print(f"[LOGGING] Error saving Q&A incrementally: {e}")
        return False




# Vertex AI Search Functions

def list_documents_in_datastore(
    project_id: str = None,
    location: str = None,
    data_store_id: str = None
) -> List[Dict[str, str]]:
    """List all documents in a Vertex AI Search data store"""
    if project_id is None:
        project_id = PROJECT_ID
    if location is None:
        location = LOCATION
    if data_store_id is None:
        data_store_id = DATA_STORE_ID
    
    client_options = ClientOptions(api_endpoint="discoveryengine.googleapis.com")
    client = discoveryengine.DocumentServiceClient(client_options=client_options)
    
    parent = client.branch_path(
        project=project_id,
        location="global",
        data_store=data_store_id,
        branch="default_branch",
    )
    
    documents = []
    
    try:
        response = client.list_documents(parent=parent)
        
        for document in response:
            doc_info = {
                'id': document.id,
                'name': document.name,
                'metadata': {}
            }
            
            if hasattr(document, 'struct_data') and document.struct_data:
                doc_info['metadata'] = document.struct_data
            
            documents.append(doc_info)
        
        return documents
        
    except Exception as e:
        parent = f"projects/{project_id}/locations/global/collections/default_collection/dataStores/{data_store_id}/branches/default_branch"
        
        try:
            response = client.list_documents(parent=parent)
            documents = []
            
            for document in response:
                doc_info = {
                    'id': document.id,
                    'name': document.name,
                    'metadata': {}
                }
                
                if hasattr(document, 'struct_data') and document.struct_data:
                    doc_info['metadata'] = document.struct_data
                
                documents.append(doc_info)
            
            return documents
            
        except Exception as e2:
            raise Exception(f"Failed to list documents: {e2}")


def search_with_chunk_augmentation(
    query: str,
    project_id: str = None,
    location: str = None,
    data_store_id: str = None,
    top_n: int = 5,
    num_chunks: int = 1
) -> List[Dict[str, Any]]:
    """Search the Vertex AI data store and return results with augmented chunks"""
    if project_id is None:
        project_id = PROJECT_ID
    if location is None:
        location = LOCATION
    if data_store_id is None:
        data_store_id = DATA_STORE_ID
    
    if num_chunks > 5:
        num_chunks = 5
    elif num_chunks < 0:
        num_chunks = 0
    
    client_options = ClientOptions(api_endpoint="discoveryengine.googleapis.com")
    client = discoveryengine_v1.SearchServiceClient(client_options=client_options)
    
    serving_config = f"projects/{project_id}/locations/global/collections/default_collection/dataStores/{data_store_id}/servingConfigs/default_search"
    
    content_search_spec = discoveryengine_v1.SearchRequest.ContentSearchSpec(
        search_result_mode=discoveryengine_v1.SearchRequest.ContentSearchSpec.SearchResultMode.CHUNKS,
        chunk_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.ChunkSpec(
            num_previous_chunks=num_chunks,
            num_next_chunks=num_chunks
        )
    )
    
    request = discoveryengine_v1.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=top_n,
        content_search_spec=content_search_spec
    )
    
    try:
        response = client.search(request)
        results = []
        count = 0
        
        for result in response.results:
            if count >= top_n:
                break
            count += 1
            
            result_data = {
                'rank': count,
                'document_metadata': {},
                'page_span': {},
                'chunks': [],
                'augmented_content': ""
            }
            
            if hasattr(result, 'chunk') and result.chunk:
                chunk = result.chunk
                
                if hasattr(chunk, 'document_metadata'):
                    result_data['document_metadata'] = {
                        'uri': getattr(chunk.document_metadata, 'uri', None),
                        'title': getattr(chunk.document_metadata, 'title', None)
                    }
                
                if hasattr(chunk, 'page_span'):
                    result_data['page_span'] = {
                        'start': getattr(chunk.page_span, 'page_start', None),
                        'end': getattr(chunk.page_span, 'page_end', None)
                    }
                
                all_chunk_content = []
                
                if hasattr(chunk.chunk_metadata, 'previous_chunks'):
                    for prev_chunk in chunk.chunk_metadata.previous_chunks:
                        result_data['chunks'].append({
                            'type': 'previous',
                            'id': prev_chunk.id,
                            'content': prev_chunk.content
                        })
                        all_chunk_content.append(prev_chunk.content)
                
                result_data['chunks'].append({
                    'type': 'relevant',
                    'id': chunk.id,
                    'content': chunk.content
                })
                all_chunk_content.append(chunk.content)
                
                if hasattr(chunk.chunk_metadata, 'next_chunks'):
                    for next_chunk in chunk.chunk_metadata.next_chunks:
                        result_data['chunks'].append({
                            'type': 'next',
                            'id': next_chunk.id,
                            'content': next_chunk.content
                        })
                        all_chunk_content.append(next_chunk.content)
                
                result_data['augmented_content'] = " ".join(all_chunk_content)
            
            results.append(result_data)
        
        return results
        
    except Exception as e:
        raise Exception(f"Search failed: {e}")


def retrieve_context_from_vertex_search(
    query: str,
    top_k: int = None,
    num_chunks: int = None
) -> List[Dict[str, Any]]:
    """Wrapper function that uses Vertex AI Search to retrieve context"""
    if top_k is None:
        top_k = TOP_K_CHUNKS
    
    search_results = search_with_chunk_augmentation(
        query=query,
        top_n=top_k,
        num_chunks=NEIGHBOUR_CHUNKS
    )
    
    contexts = []
    for i, result in enumerate(search_results):
        context = {
            'chunk_text': result['augmented_content'],
            'distance': i / len(search_results),
            'metadata': result['document_metadata'],
            'chunks': result['chunks']
        }
        contexts.append(context)
    
    return contexts


def list_chunks_for_document(
    document_id: str,
    project_id: str = None,
    location: str = None,
    data_store_id: str = None
) -> List[Dict[str, Any]]:
    """List all chunks for a specific document in Vertex AI Search"""
    if project_id is None:
        project_id = PROJECT_ID
    if location is None:
        location = LOCATION
    if data_store_id is None:
        data_store_id = DATA_STORE_ID
    
    client_options = ClientOptions(api_endpoint="discoveryengine.googleapis.com")
    
    try:
        # Try using the v1alpha client which has chunk support
        from google.cloud import discoveryengine_v1alpha
        client = discoveryengine_v1alpha.ChunkServiceClient(client_options=client_options)
        
        # The full resource name of the document
        parent = f"projects/{project_id}/locations/global/collections/default_collection/dataStores/{data_store_id}/branches/default_branch/documents/{document_id}"
        
        # List chunks using the correct method
        chunks = []
        page_result = client.list_chunks(parent=parent)
        
        for chunk in page_result:
            chunk_data = {
                'id': chunk.id,
                'name': chunk.name,
                'content': chunk.content,
                'page_span': {
                    'start': getattr(chunk.page_span, 'page_start', None) if hasattr(chunk, 'page_span') else None,
                    'end': getattr(chunk.page_span, 'page_end', None) if hasattr(chunk, 'page_span') else None
                }
            }
            chunks.append(chunk_data)
        
        return chunks
        
    except ImportError:
        print("Warning: discoveryengine_v1alpha not available, using alternative approach")
        # Alternative: Use search to get chunks for the document
        return get_document_chunks_via_search(document_id, project_id, location, data_store_id)
    except Exception as e:
        print(f"Error listing chunks for document {document_id}: {e}")
        # Fallback to search-based approach
        return get_document_chunks_via_search(document_id, project_id, location, data_store_id)


def get_document_chunks_via_search(
    document_id: str,
    project_id: str = None,
    location: str = None,
    data_store_id: str = None
) -> List[Dict[str, Any]]:
    """Alternative method to get document chunks using search API"""
    if project_id is None:
        project_id = PROJECT_ID
    if location is None:
        location = LOCATION
    if data_store_id is None:
        data_store_id = DATA_STORE_ID
    
    try:
        # Use a search query to get chunks from this specific document
        # We'll search for common words to get a broad set of chunks
        search_queries = ["the", "a", "and", "or", "in", "of", "to", "for"]
        all_chunks = []
        seen_chunk_ids = set()
        
        for query in search_queries:
            results = search_with_chunk_augmentation(
                query=query,
                top_n=50,  # Get many results
                num_chunks=0  # Just get the relevant chunk
            )
            
            for result in results:
                # Filter chunks by document
                if 'document_metadata' in result and result['document_metadata'].get('uri', '').endswith(document_id):
                    for chunk in result.get('chunks', []):
                        chunk_id = chunk.get('id')
                        if chunk_id and chunk_id not in seen_chunk_ids:
                            seen_chunk_ids.add(chunk_id)
                            all_chunks.append({
                                'id': chunk_id,
                                'name': chunk.get('name', ''),
                                'content': chunk.get('content', ''),
                                'page_span': {}
                            })
        
        # Sort chunks by ID to maintain order
        all_chunks.sort(key=lambda x: x['id'])
        
        print(f"Retrieved {len(all_chunks)} unique chunks for document via search")
        return all_chunks
        
    except Exception as e:
        print(f"Error getting chunks via search: {e}")
        return []


def merge_chunks_into_bigger_chunks(
    chunks: List[Dict[str, Any]],
    merge_count: int = 3
) -> List[Dict[str, Any]]:
    """Merge consecutive chunks into bigger chunks
    
    Args:
        chunks: List of chunk dictionaries with 'content' field
        merge_count: Number of chunks to merge together (default: 3)
    
    Returns:
        List of bigger chunks
    """
    if not chunks:
        return []
    
    bigger_chunks = []
    
    # Process chunks in groups of merge_count
    for i in range(0, len(chunks), merge_count):
        # Get the slice of chunks to merge
        chunk_slice = chunks[i:i+merge_count]
        
        # Merge the content
        merged_content = " ".join([chunk['content'] for chunk in chunk_slice])
        
        # Create the bigger chunk
        bigger_chunk = {
            'content': merged_content,
            'chunk_ids': [chunk['id'] for chunk in chunk_slice],
            'chunk_count': len(chunk_slice),
            'start_index': i,
            'end_index': min(i + merge_count - 1, len(chunks) - 1)
        }
        
        # If chunks have page spans, calculate the combined span
        if 'page_span' in chunk_slice[0] and chunk_slice[0]['page_span']['start'] is not None:
            bigger_chunk['page_span'] = {
                'start': chunk_slice[0]['page_span']['start'],
                'end': chunk_slice[-1]['page_span']['end']
            }
        
        bigger_chunks.append(bigger_chunk)
    
    return bigger_chunks


# Context Generation Functions

def clue_generator(text, model=None):
    """Generate clues from text"""
    if model is None:
        model = GenerativeModel("gemini-1.5-pro")
    
    prompt = f"""
  Reference Text:
  {text}

  Task:
  You are a reference question creator. Imagine the provided text is a section from a comprehensive reference document. Based **solely** on the given Reference Text, formulate a set of insightful questions with corresponding reasoning.  Each question must be answerable **exclusively** using the information found within the provided text. Do not use any external knowledge or information.

  Each question you generate should be:

  1.  **Directly Relevant:** The question must pertain specifically to the content of the Reference Text.
  2.  **Comprehensive:**  The questions, as a whole, should reflect the major themes and key details present in the Reference Text.
  3.  **Sound and Logical:** The questions should be well-formed, clear, and appropriate for a reference context. Consider what a reader might realistically want to learn from this text if it were part of a larger reference work.
  4.  **Standalone:** The question should be self-contained and understandable without directly referencing the provided text. Avoid phrases like "According to the text..." or "In the passage...". Imagine someone encountering the question in isolation; it should still be clear and answerable.

  For each question, provide a "chain-of-thought" explanation detailing why the question is relevant and answerable using only the Reference Text.

  Use this JSON schema for your response:
  ```json
  {{
    "questions": [
      {{
        "chain_of_thought": "Reasoning for why this question is relevant and answerable based on the text.",
        "question": "The question itself."
      }}
    ]
  }}
  ```
  """
    
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            response = model.generate_content(prompt)
            response_clean = clean_json_string(response)
            return json.loads(response_clean)
        except Exception as e:
            print(f"Attempt {retries + 1} failed: {e}")
            retries += 1
            if retries < MAX_RETRIES:
                time.sleep(2 * retries)  # Exponential backoff
    
    # Raise exception to skip this iteration
    print(f"[LOGGING] Max retries ({MAX_RETRIES}) reached in clue_generator.")
    raise Exception(f"Failed to generate clues after {MAX_RETRIES} attempts")


def targeted_information_seeking(query, model=None):
    """Generate targeted information for a query"""
    if model is None:
        model = GenerativeModel("gemini-1.5-pro")
    
    prompt = f"""
  You are a helpful information retrieval assistant.
  I will give you a query, and you need to perform the following three tasks:

  1. **Describe Text:** Provide a concise description of the type of text that would be most relevant for answering the query. Specify the kind of document (e.g., scientific paper, news article, blog post, book chapter), its potential topics, and any specific details that would make it useful.
  2. **Original Question:** Rephrase the query as a clear and concise question. This helps ensure we understand the user's intent.
  3. **Hypothetical Example:** Create a hypothetical excerpt (around 50-100 words) of text that could be part of a relevant document. This example should demonstrate the type of information, style, and level of detail expected in a helpful answer.

  Here is the query: "{query}"

  Format your response as a JSON object with the following keys:
  ```json
  {{
    "description": "[Your description here]",
    "original_question": "[Your rephrased question here]",
    "hypothetical_example": "[Your example here]"
  }}
  """
    
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            response = model.generate_content(prompt)
            response = clean_json_string(response)
            return json.loads(response)
        except Exception as e:
            print(f"Attempt {retries + 1} failed: {e}")
            retries += 1
            if retries < MAX_RETRIES:
                time.sleep(2 * retries)  # Exponential backoff
    
    # Raise exception to skip this iteration
    print(f"[LOGGING] Max retries ({MAX_RETRIES}) reached in targeted_information_seeking.")
    raise Exception(f"Failed to generate targeted information after {MAX_RETRIES} attempts")


def extract_text_blocks_with_index_and_aggregation(text, threshold=30):
    """Extract text blocks with index and aggregation"""
    blocks = []
    current_index = 0
    
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        lines = paragraph.strip().split('\n')
        if len(lines) > 1 and len(set(len(line.split('|')) for line in lines)) == 1 and lines[0].count('|') > 1:
            blocks.append({'type': 'table', 'content': lines, 'index': current_index})
            current_index += 1
        else:
            sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', paragraph)
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    blocks.append({'type': 'sentence', 'content': sentence, 'index': current_index})
                    current_index += 1
    
    # Aggregate short elements
    aggregated_blocks = []
    i = 0
    while i < len(blocks):
        current_block = blocks[i]
        if (len(current_block['content']) if isinstance(current_block['content'], str) else sum(len(line) for line in current_block['content']) < threshold) and i + 1 < len(blocks):
            next_block = blocks[i + 1]
            new_content = []
            
            if current_block['type'] == 'table':
                new_content.extend(current_block['content'])
            else:
                new_content.append(current_block['content'])
            
            if next_block['type'] == 'table':
                new_content.extend(next_block['content'])
            else:
                new_content.append(next_block['content'])
            
            aggregated_blocks.append({
                'type': 'aggregated',
                'content': new_content,
                'index': current_block['index']
            })
            i += 2
        else:
            aggregated_blocks.append(current_block)
            i += 1
    
    return aggregated_blocks


def find_relevant_overall_blocks_with_gemini(blocks, target_info, model=None):
    """Find relevant blocks using Gemini"""
    if model is None:
        model = GenerativeModel("gemini-1.5-pro")
    
    prompt = f"""
    You are a helpful assistant tasked with identifying relevant information from a text.

    Here is a text that has been broken down into blocks, each with an index:

    {blocks}

    ---------------------

    Here is the target information you need to consider:

    Question: {target_info["original_question"]}
    Description: {target_info["description"]}

    ---------------------

    Your task is to carefully analyze the text blocks and determine which indexes contain information that is:

    1.  Directly relevant to answering the question.
    2.  Closely related to the provided description.
    3.  Potentially useful for understanding the context of the question or description.

    Return ONLY a list of the indexes that you believe are relevant. Do not include any explanations or additional text. If no indexes are relevant, return an empty list.

    For example, if indexes 0, 2, and 5 are relevant, your response should be:

    [0, 2, 5]
    """
    
    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt)
            relevant_indexes_str = response.text
            
            if relevant_indexes_str.strip() == '[]':
                relevant_indexes = []
            else:
                relevant_indexes = eval(relevant_indexes_str)
            return relevant_indexes
        except Exception as e:
            print(f"[LOGGING] Attempt {attempt + 1} failed in find_relevant_overall_blocks: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 * (attempt + 1))  # Exponential backoff
    
    # Return empty list on failure (this is non-critical, so we can continue)
    print(f"[LOGGING] Max retries ({MAX_RETRIES}) reached in find_relevant_overall_blocks_with_gemini")
    return []


def find_relevant_individual_blocks_with_gemini(block, target_info, model=None):
    """Find relevant individual blocks with Gemini"""
    if model is None:
        model = GenerativeModel("gemini-1.5-pro")
    
    prompt_1 = f"""
    You are a helpful assistant tasked with determining the relevance of a single text block to a specific question and its description.

    Here is the text block with its index:

    {block}

    ---------------------

    Here is the target information you need to consider:

    Question: {target_info["original_question"]}
    Description: {target_info["description"]}

    ---------------------

    Your task is to carefully analyze the provided text block and determine whether it is relevant to the question and description. Consider the following criteria for relevance:

    1.  **Directly relevant:** The text block contains information that directly answers the question or is explicitly mentioned in the description.
    2.  **Closely related:** The text block contains information that is closely related to the question or description, even if not a direct answer. This includes synonyms, related concepts, or supporting details.
    3.  **Potentially useful:** The text block contains information that, while not directly or closely related, might offer valuable context, background information, or insights that could be helpful in understanding the question or description fully.
    4.  **Tangentially related:** The text block contains information that has even a remote connection to the question or description. Think broadly and consider any possible link, no matter how small.

    You should provide your response in JSON format with two parts:

    1.  **chain_of_thought:**  A detailed explanation of your reasoning process. Describe how you analyzed the text block's relevance based on the criteria above. Explain why you believe the text is or is not relevant.
    2.  **relevant_indexes:** If the text block is relevant based on the criteria above, this should be a list containing the index of the block. If the block is not relevant, this should be an empty list.

    **Example Output:**

    ```json
    {{
        "chain_of_thought": "The text block discusses the history of the company, which is not directly related to the question about their current CEO. However, the description mentions understanding the company's background, so this historical information could be considered potentially useful for context. Therefore, I deem it relevant.",
        "relevant_indexes": [3]
    }}
    ```

    OR

    ```json
    {{
        "chain_of_thought": "The text block describes a specific type of flower, while the question asks about a specific type of tree. There is no clear connection between the two, and the description doesn't mention anything related to flowers. Therefore, I deem this text block irrelevant.",
        "relevant_indexes": []
    }}
    ```
    """
    
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            response = model.generate_content(prompt_1)
            response = clean_json_string(response)
            return json.loads(response)
        except Exception as e:
            print(f"Attempt {retries + 1} failed: {e}")
            retries += 1
            if retries < MAX_RETRIES:
                time.sleep(2 * retries)  # Exponential backoff
    
    # Return empty result (this is non-critical, individual blocks can fail)
    print(f"[LOGGING] Max retries ({MAX_RETRIES}) reached in find_relevant_individual_blocks_with_gemini")
    return {"chain_of_thought": "Failed to process due to API errors", "relevant_indexes": []}


def extract_relevant_text(blocks, target_info, model=None):
    """Extract relevant text from blocks"""
    if model is None:
        model = GenerativeModel("gemini-1.5-pro")
    
    relevant_indices = set()
    
    # Process individual blocks with delay to avoid overwhelming API
    print(f"[LOGGING] Processing {len(blocks)} blocks for relevance")
    for idx, block in enumerate(blocks):
        try:
            if idx > 0 and idx % 5 == 0:  # Add delay every 5 blocks
                print(f"[LOGGING] Processed {idx}/{len(blocks)} blocks, pausing...")
                time.sleep(3)
            
            result = find_relevant_individual_blocks_with_gemini(block, target_info, model)
            
            if isinstance(result, dict) and "relevant_indexes" in result and result["relevant_indexes"]:
                relevant_indices.update(result["relevant_indexes"])
        except Exception as e:
            print(f"[LOGGING] Error processing block {idx}: {e}")
            continue  # Skip this block and continue with others
    
    # Process overall blocks with error handling
    try:
        print(f"[LOGGING] Finding overall relevant blocks")
        overall_result = find_relevant_overall_blocks_with_gemini(blocks, target_info, model)
        if isinstance(overall_result, list):
            relevant_indices_1 = set(overall_result)
        else:
            print(f"[LOGGING] Unexpected result from find_relevant_overall_blocks: {type(overall_result)}")
            relevant_indices_1 = set()
    except Exception as e:
        print(f"[LOGGING] Error in find_relevant_overall_blocks: {e}")
        relevant_indices_1 = set()
    
    relevant_indices_2 = relevant_indices_1 | relevant_indices
    
    relevant_blocks = [block for block in blocks if block['index'] in relevant_indices_2]
    relevant_blocks.sort(key=lambda x: x['index'])
    
    relevant_text = ""
    for block in relevant_blocks:
        if block['type'] == 'aggregated':
            relevant_text += " ".join(block['content']) + " "
        else:
            relevant_text += " ".join(block['content']) + " "
    
    return relevant_text.strip()


def find_aggregate_relevant_indices(retrived_contexts, target_info, model=None):
    """Find aggregate relevant indices"""
    if model is None:
        model = GenerativeModel("gemini-1.5-pro")
    
    context = []
    for i in range(len(retrived_contexts)):
        try:
            print(f"[LOGGING] Processing context {i+1}/{len(retrived_contexts)}")
            ref = retrived_contexts[i]["chunk_text"]
            indexed_ref = extract_text_blocks_with_index_and_aggregation(ref)
            
            # Add retry logic for extract_relevant_text
            retry_delay = 5  # seconds
            
            for attempt in range(MAX_RETRIES):
                try:
                    print(f"[LOGGING] Extracting relevant text - attempt {attempt + 1}")
                    tergeted_text = extract_relevant_text(indexed_ref, target_info, model)
                    context.append(tergeted_text)
                    break  # Success, exit retry loop
                except Exception as e:
                    print(f"[LOGGING] Error in extract_relevant_text attempt {attempt + 1}: {e}")
                    if attempt < MAX_RETRIES - 1:
                        print(f"[LOGGING] Waiting {retry_delay} seconds before retry...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        print(f"[LOGGING] Max retries ({MAX_RETRIES}) reached for context {i+1}, using empty text")
                        context.append("")  # Add empty text to maintain order
            
            # Add delay between contexts to avoid overwhelming the API
            if i < len(retrived_contexts) - 1:
                time.sleep(2)
                
        except Exception as e:
            print(f"[LOGGING] Error processing context {i+1}: {e}")
            context.append("")  # Add empty text to maintain order
    
    return context


# QA Generation Functions

def qa_profile_gen(context, parameter_json, model=None):
    """Generate QA profiles"""
    if model is None:
        model = GenerativeModel("gemini-1.5-pro")
    
    # Extract dimension names dynamically
    dimensions = validate_qa_profiles(parameter_json)
    
    # Build dimension list for prompt
    dimension_list = ", ".join([f"`{dim}`" for dim in dimensions])
    
    # Build example values for each dimension
    profiles_dict = json.loads(parameter_json) if isinstance(parameter_json, str) else parameter_json
    dimension_examples = []
    for dim in dimensions:
        if dim in profiles_dict["parameters"] and "values" in profiles_dict["parameters"][dim]:
            values = list(profiles_dict["parameters"][dim]["values"].keys())
            examples = ", ".join(values[:3])  # Show first 3 examples
            dimension_examples.append(f'"{dim}": "Selected {dim} (e.g., {examples})"')
    
    dimension_json_template = ",\n        ".join(dimension_examples)
    
    prompt = f'''
    You are a Question-Answer Generation Strategist. Your task is to analyze a provided text (Reference Text) and a set of parameters (QA Generation Parameters) to generate a question that focuses on the **whole scope** of the text, utilizing the specified parameters.

    **Input:**

    1.  **Reference Text:**
        ```
        {context}
        ```

    2.  **QA Generation Parameters:**
        ```json
        {parameter_json}
        ```

    **Task:**

    Carefully consider the **Reference Text** and the detailed descriptions within the **QA Generation Parameters**. Identify and suggest the top 5 most suitable combinations of {dimension_list} (profiles) that would lead to the generation of high-quality, insightful, and textually-grounded question-answer pairs.

    Strive for maximum diversity among your 5 selected profiles. Choose combinations that represent significantly different approaches to questioning the Reference Text. This means varying all dimensions ({dimension_list}) as much as reasonably possible while still adhering to the core constraints.

    For each suggested profile, provide a clear rationale explaining why the chosen attributes are appropriate given the specific content and nature of the **Reference Text**.

    **Important:**

    *   The question which will be constructed based on the selected profile must always pertain to the **whole** scope of the provided text.
    *   The dimensions ({dimension_list}) must be selected in a way that makes sense for the given text and allows for a meaningful question to be generated about the entire document.
    *   Provide a brief explanation justifying your choice for each dimension.
    *   Diversity Requirement: Ensure that the selected profiles are as divergent as possible in their approaches. Prioritize variety across all dimensions in the 5 profiles.

    **Output:**

    Use the following JSON format for your response:
    ```json
    {{
    "QA_generator_profiles": [
        {{
        "reason_for_profile": "Reasoning for selecting this specific combination",
        {dimension_json_template}
        }},
        // ... (More profiles if applicable)
    ]
    }}
    ```
    '''
    
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            response = model.generate_content(prompt)
            response = clean_json_string(response)
            return json.loads(response)
        except Exception as e:
            print(f"Attempt {retries + 1} failed: {e}")
            retries += 1
            if retries < MAX_RETRIES:
                time.sleep(2 * retries)  # Exponential backoff
    
    # Raise exception to skip this iteration
    print(f"[LOGGING] Max retries ({MAX_RETRIES}) reached in qa_profile_gen.")
    raise Exception(f"Failed to generate QA profiles after {MAX_RETRIES} attempts")


def qa_gen(context, QA_gen_profiles_json, profile_char, model=None):
    """Generate QA based on context and profile"""
    if model is None:
        model = GenerativeModel("gemini-1.5-pro")
    
    # Build the profile description dynamically
    profile_descriptions = []
    for dim_key, value_key in profile_char.items():
        # Try to get the full description, fall back to simple format if not found
        dim_value = get_dimension_value(QA_gen_profiles_json, dim_key, value_key)
        profile_descriptions.append(f"{dim_key}: {dim_value}")
    
    profile_section = "\n\n    ".join(profile_descriptions)
    
    prompt = f"""
    Reference Text:

    {context}

    Task:

    You are a reference question-answer creator. Imagine the provided Reference Text is a collection of parts that share a main theme from a comprehensive reference document. Based solely on the given Reference Text, formulate one insightful question and its corresponding answer. The question and answer must be derived exclusively from the information found within the provided Reference Text. Do not use any external knowledge or information beyond what is provided in the Reference Text.

    Requirements:

    Self-Contained Question and Answer Generation: The LLM must generate question and answer pairs where both the question and its corresponding answer are entirely self-contained and comprehensible in isolation. The question should be framed in a general and standalone manner, without making any direct or indirect references to a provided source document or text, avoiding phrases like "according to the document" or "in the passage" or "like in this document". Similarly, the answer must also avoid referencing the source document directly. Both question and answer should use clear and explicit language, avoid ambiguous references, and explicitly identify all entities and contexts within themselves. Each pair must be fully understandable without requiring any external information or context beyond what is directly stated within that specific question and answer.

    {profile_section}

    Comprehensiveness: The question should be crafted in a way that necessitates the consideration of all parts of the provided Reference Text to arrive at a complete and accurate answer. Strive to create a question that cannot be answered by focusing on only a small portion of the Reference Text. The ideal question will require synthesizing information from across the entire provided Reference Text.

    For the question and answer, provide a "chain_of_thought" explanation detailing why the question is relevant, given the specified profile parameters, and how the answer can be derived using only the Reference Text.

    Use this JSON schema for your response:
    ```json
    {{
        "question": {{
        "chain_of_thought": "Reasoning for why this question is relevant given the profile parameters and how it's answerable based on the Reference Text.",
        "question": "The question itself (standalone and without direct reference to the Reference Text)."
        }},
        "answer": {{
        "chain_of_thought": "Explanation of how the answer is derived solely from the provided Reference Text, potentially referencing specific phrases or sentences from multiple parts of the Reference Text to demonstrate the comprehensive nature of the question.",
        "answer": "The answer to the question, based only on the information in the Reference Text."
        }}
    }}
    """
    
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            response = model.generate_content(prompt)
            response = clean_json_string(response)
            return json.loads(response)
        except Exception as e:
            print(f"Attempt {retries + 1} failed: {e}")
            retries += 1
            if retries < MAX_RETRIES:
                time.sleep(2 * retries)  # Exponential backoff
    
    # Raise exception to skip this iteration
    print(f"[LOGGING] Max retries ({MAX_RETRIES}) reached in qa_gen.")
    raise Exception(f"Failed to generate Q&A after {MAX_RETRIES} attempts")


def review_text(input_text, model=None):
    """Review text with multi-agent critics"""
    if model is None:
        model = GenerativeModel("gemini-1.5-pro")
    
    critics = {
        "Analyst": "Meticulous and logical. Prioritizes accuracy, completeness, and coherence. Focuses on core intent and avoids ambiguities.",
        "Synthesizer": "Broad-thinking and insightful. Values conciseness and clarity. Seeks insightful connections and novel perspectives within the context.",
        "Practical": "Practical and results-oriented. Prioritizes specificity, relevance, and real-world applicability. Focuses on actionable information."
    }
    
    criteria = """
    Approval Criteria:
    1. The question and answer are standalone, clear, and well-formed
    2. The answer can be inferred from the provided context
    3. The answer contains only information present in the context (no external knowledge)
    4. The answer directly and completely addresses the question
    5. The content is appropriate and free from harmful, biased, or offensive material
    """
    
    def get_critic_review_first_round(persona, persona_desc, text):
        prompt = f"""
        As a {persona} critic with the following description: {persona_desc}

        Please review the following text based on these criteria:
        {criteria}

        Text to review:
        "{text}"

        Considering other critics' opinions, provide your final decision (APPROVED or REJECTED) and reasoning.
        Format: DECISION: [Your decision]
        REASONING: [Your detailed reasoning]
        """
        
        retries = 0
        
        while retries < MAX_RETRIES:
            try:
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                print(f"Attempt {retries + 1} failed: {e}")
                retries += 1
                if retries < MAX_RETRIES:
                    time.sleep(2 * retries)  # Exponential backoff
        
        return None
    
    def get_critic_review_second_round(persona, persona_desc, text, other_reviews):
        prompt = f"""
        As a {persona} critic with the following description: {persona_desc}

        Consider last round critics' reviews:
        {other_reviews}

        Please review the following text based on these criteria:
        {criteria}

        Text to review:
        "{text}"

        Considering other critics' opinions, provide your final decision (APPROVED or REJECTED) and reasoning.
        Format: DECISION: [Your decision]
        REASONING: [Your detailed reasoning]
        """
        
        retries = 0
        
        while retries < MAX_RETRIES:
            try:
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                print(f"Attempt {retries + 1} failed: {e}")
                retries += 1
                if retries < MAX_RETRIES:
                    time.sleep(2 * retries)  # Exponential backoff
        
        return None
    
    # First round of reviews
    first_round = {}
    for critic, desc in critics.items():
        review = get_critic_review_first_round(critic, desc, input_text)
        if review:
            first_round[critic] = review
        time.sleep(1)
    
    # Check if all critics agree
    decisions = [review.split('DECISION:')[1].split('REASONING:')[0].strip()
                for review in first_round.values()]
    
    if len(set(decisions)) == 1:
        final_decision = decisions[0]
        reasons = [review.split('REASONING:')[1].strip() for review in first_round.values()]
        final_reasoning = " Combined reasoning: " + "; ".join(reasons)
        return final_decision, final_reasoning
    
    # Second round if there's disagreement
    disagreement_summary = "\n".join([f"{critic}: {review}"
                                    for critic, review in first_round.items()])
    
    second_round = {}
    for critic, desc in critics.items():
        review = get_critic_review_second_round(critic, desc, input_text, disagreement_summary)
        if review:
            second_round[critic] = review
        time.sleep(1)
    
    # Get majority decision
    final_decisions = [review.split('DECISION:')[1].split('REASONING:')[0].strip()
                      for review in second_round.values()]
    
    majority_decision = max(set(final_decisions), key=final_decisions.count)
    
    # Combine reasoning from critics who agreed with majority
    majority_reasons = [review.split('REASONING:')[1].strip()
                       for critic, review in second_round.items()
                       if majority_decision in review]
    
    final_reasoning = " Majority reasoning: " + "; ".join(majority_reasons)
    
    return majority_decision, final_reasoning


# Load QA Profiles from external JSON file
QA_PROFILES_FILE = "qa_profiles.json"

def load_qa_profiles(profiles_file_path=None):
    """Load QA profiles from external JSON file
    
    Args:
        profiles_file_path: Optional path to QA profiles JSON file. 
                          If not provided, looks for qa_profiles.json in script directory.
    """
    # Use provided path or default
    if profiles_file_path:
        qa_profiles_file = profiles_file_path
    else:
        qa_profiles_file = QA_PROFILES_FILE
    
    try:
        # First try the exact path provided
        if os.path.exists(qa_profiles_file):
            with open(qa_profiles_file, 'r', encoding='utf-8') as f:
                print(f"Loaded QA profiles from: {qa_profiles_file}")
                return json.dumps(json.load(f))
        
        # If not found and no custom path was provided, try script directory
        if not profiles_file_path:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            profiles_path = os.path.join(script_dir, qa_profiles_file)
            
            if os.path.exists(profiles_path):
                with open(profiles_path, 'r', encoding='utf-8') as f:
                    print(f"Loaded QA profiles from: {profiles_path}")
                    return json.dumps(json.load(f))
        
        print(f"Warning: QA profiles file '{qa_profiles_file}' not found. Using default profiles.")
        # Return default minimal profile as fallback
        return json.dumps(get_default_qa_profiles())
    except Exception as e:
        print(f"Error loading QA profiles: {e}")
        print("Using default profiles as fallback.")
        # Return minimal default profile
        return json.dumps(get_default_qa_profiles())

def get_default_qa_profiles():
    """Get default QA profiles structure"""
    return {
        "parameters": {
            "Type": {
                "description": "Question type",
                "values": {
                    "How-to": {"description": "Step-by-step guide"},
                    "Explanatory": {"description": "Why or how something works"}
                }
            },
            "Persona": {
                "description": "Who is asking",
                "values": {
                    "The Expert": {"description": "Advanced user"},
                    "The Novice": {"description": "Beginner"}
                }
            },
            "Difficulty": {
                "description": "Answer complexity",
                "values": {
                    "Easy": {"description": "Direct answer"},
                    "Hard": {"description": "Requires inference"}
                }
            }
        }
    }

# QA profiles will be loaded in main() after parsing arguments
QA_gen_profiles = None

def validate_qa_profiles(qa_profiles_json):
    """Validate the structure of QA profiles and extract dimension names"""
    try:
        profiles_dict = json.loads(qa_profiles_json) if isinstance(qa_profiles_json, str) else qa_profiles_json
        
        if "parameters" not in profiles_dict:
            raise ValueError("QA profiles must contain 'parameters' key")
        
        dimensions = list(profiles_dict["parameters"].keys())
        
        # Validate each dimension has required structure
        for dim in dimensions:
            if "values" not in profiles_dict["parameters"][dim]:
                raise ValueError(f"Dimension '{dim}' must contain 'values' key")
            if "description" not in profiles_dict["parameters"][dim]:
                print(f"Warning: Dimension '{dim}' missing 'description' key")
        
        return dimensions
    except Exception as e:
        print(f"Error validating QA profiles: {e}")
        # Return default dimensions as fallback
        return ["Type", "Persona", "Scope", "Difficulty"]

def get_dimension_value(qa_profiles_json, dimension, value_key):
    """Safely get a dimension value from the profiles JSON"""
    try:
        profiles_dict = json.loads(qa_profiles_json) if isinstance(qa_profiles_json, str) else qa_profiles_json
        return profiles_dict["parameters"][dimension]["values"][value_key]
    except KeyError:
        # Return a basic description if the exact path doesn't exist
        return {"description": f"{dimension}: {value_key}"}
    except Exception as e:
        print(f"Error getting dimension value for {dimension}/{value_key}: {e}")
        return {"description": f"{dimension}: {value_key}"}




# Main Orchestration Function

def main_benchmark_gen_vertex_search(
    doc_index_up=2,
    chunk_index_up=2,
    clue_index_up=2,
    profile_index_up=2,
    benchmark=[],
    chunks_to_merge=3,
    output_file=None,
    llm_model="gemini-2.0-flash"
):
    """Enhanced version that works directly with Vertex AI Search
    
    Args:
        doc_index_up: Number of documents to process
        chunk_index_up: Number of big chunks to process per document
        clue_index_up: Number of clues per big chunk
        profile_index_up: Number of profiles per clue
        benchmark: Existing benchmark list to append to
        chunks_to_merge: Number of chunks to merge into bigger chunks (default: 3)
        output_file: Path to save the benchmark incrementally (optional)
        llm_model: Specfic model to be used in all functions that use llm decoder
    """
    print(f"\n[LOGGING] Starting main_benchmark_gen_vertex_search function")
    print(f"[LOGGING] Parameters: doc_index_up={doc_index_up}, chunk_index_up={chunk_index_up}, clue_index_up={clue_index_up}, profile_index_up={profile_index_up}, chunks_to_merge={chunks_to_merge}")
    
    # Initialize the output file if provided
    if output_file:
        print(f"[LOGGING] Initializing output file: {output_file}")
        try:
            # Initialize with empty list
            with open(output_file, 'w') as f:
                json.dump([], f)
            print(f"[LOGGING] Output file initialized successfully")
        except Exception as e:
            print(f"[LOGGING] Error initializing output file: {e}")
            print(f"Warning: Could not initialize output file {output_file}: {e}")
            output_file = None  # Disable incremental save if initialization fails
    
    try:
        #model_1 = GenerativeModel("gemini-2.5-pro")
        #model_1 = GenerativeModel("gemini-2.5-flash")
        model_1 = GenerativeModel(llm_model)
        
        print("Using Vertex AI Search for document retrieval...")
        print(f"Data Store ID: {DATA_STORE_ID}")
        
        # List documents from Vertex AI Search
        try:
            print(f"[LOGGING] About to call list_documents_in_datastore()")
            documents = list_documents_in_datastore()
            print(f"[LOGGING] Successfully listed documents")
            print(f"Found {len(documents)} documents in Vertex AI Search")
            
            if not documents:
                print("No documents found in data store!")
                return benchmark
                
        except Exception as e:
            print(f"Error listing documents: {e}")
            # If listing fails, create a dummy document list for testing
            documents = [{"id": "doc1", "name": "Document 1"}]
            print("Using dummy document for testing")
        
        # Process documents
        docs_to_process = min(doc_index_up, len(documents))
        selected_docs = random.sample(documents, docs_to_process)
        
        print(f"\n{'='*80}")
        print(f"Randomly selected {docs_to_process} documents to process")
        print(f"{'='*80}")
        
        overall_progress = 1
        total_expected = docs_to_process * chunk_index_up * clue_index_up * profile_index_up
        
        # Note: Sample queries are no longer needed since we're listing chunks directly by document
        
        for doc_idx, doc in enumerate(selected_docs):
            doc_name = doc.get('name', doc.get('id', f'doc_{doc_idx}'))
            doc_id = doc.get('id', doc_name)
            
            print(f"\n[LOGGING] Entering document loop - iteration {doc_idx + 1}/{docs_to_process}")
            
            try:
                print(f"\n{'#'*80}")
                print(f"Processing document {doc_idx + 1}/{docs_to_process}: {doc_name}")
                print(f"Document ID: {doc_id}")
                print(f"{'#'*80}")
                
                # List all chunks for this specific document
                print(f"[LOGGING] About to call list_chunks_for_document for doc_id: {doc_id}")
                document_chunks = list_chunks_for_document(doc_id)
                print(f"[LOGGING] Completed list_chunks_for_document")
                
                if not document_chunks:
                    print(f"No chunks found for document {doc_name}, skipping...")
                    continue
                
                print(f"Found {len(document_chunks)} chunks for document {doc_name}")
                
                # Merge chunks into bigger chunks
                print(f"[LOGGING] About to merge chunks - merging {chunks_to_merge} chunks each")
                bigger_chunks = merge_chunks_into_bigger_chunks(document_chunks, chunks_to_merge)
                print(f"[LOGGING] Completed merging chunks")
                print(f"Created {len(bigger_chunks)} bigger chunks (merging {chunks_to_merge} chunks each)")
                
                # Randomly select bigger chunks to process
                big_chunks_to_process = min(chunk_index_up, len(bigger_chunks))
                selected_big_chunk_indices = random.sample(range(len(bigger_chunks)), big_chunks_to_process)
                
                for big_chunk_idx, big_chunk_index in enumerate(selected_big_chunk_indices):
                    print(f"\n[LOGGING] Entering big chunk loop - iteration {big_chunk_idx + 1}/{big_chunks_to_process}")
                    big_chunk = bigger_chunks[big_chunk_index]
                    chunk_text = big_chunk['content']
                    
                    print(f"\n{'='*60}")
                    print(f"Document: {doc_name} | Big Chunk {big_chunk_idx + 1}/{big_chunks_to_process}")
                    print(f"Merged chunks: {big_chunk['start_index']} to {big_chunk['end_index']} ({big_chunk['chunk_count']} chunks)")
                    
                    try:
                        print(f"[LOGGING] About to call clue_generator")
                        clue_list = clue_generator(chunk_text, model_1)['questions']
                        print(f"[LOGGING] Completed clue_generator")
                        print(f"Generated {len(clue_list)} clues")
                        
                        clues_to_process = min(clue_index_up, len(clue_list))
                        selected_clue_indices = random.sample(range(len(clue_list)), clues_to_process)
                        
                        for clue_idx, clue_index in enumerate(selected_clue_indices):
                            print(f"\n[LOGGING] Entering clue loop - iteration {clue_idx + 1}/{clues_to_process}")
                            print(f"\n{'-'*40}")
                            print(f"Document: {doc_name} | Clue {clue_idx + 1}/{clues_to_process}")
                            
                            try:
                                clue = clue_list[clue_index]['question']
                                print(f"[LOGGING] About to call targeted_information_seeking")
                                extended_clue = targeted_information_seeking(clue, model_1)
                                print(f"[LOGGING] Completed targeted_information_seeking")
                                utilized_extended_clue = extended_clue["hypothetical_example"] + extended_clue["description"]
                                
                                print(f"[LOGGING] About to call retrieve_context_from_vertex_search")
                                retrieved_contexts = retrieve_context_from_vertex_search(utilized_extended_clue)
                                print(f"[LOGGING] Completed retrieve_context_from_vertex_search")
                                
                                print(f"[LOGGING] About to call find_aggregate_relevant_indices")
                                aggregated_indices_text = find_aggregate_relevant_indices(retrieved_contexts, extended_clue, model_1)
                                print(f"[LOGGING] Completed find_aggregate_relevant_indices")

                                if len(" ".join(filter(None, aggregated_indices_text)).strip())<10:
                                    print("[LOGGING] Aggregated context is too short (< 10 chars), skipping to next iteration.")
                                    overall_progress += 1
                                    continue
                                
                                print(f"[LOGGING] About to call qa_profile_gen")
                                suggested_qa_gen_profile = qa_profile_gen(aggregated_indices_text, QA_gen_profiles, model_1)
                                print(f"[LOGGING] Completed qa_profile_gen")
                                
                                QA_gen_profiles_json = json.loads(QA_gen_profiles)
                                print(f"Suggested {len(suggested_qa_gen_profile['QA_generator_profiles'])} profiles")
                                
                                profiles_to_process = min(profile_index_up, len(suggested_qa_gen_profile['QA_generator_profiles']))
                                selected_profile_indices = random.sample(range(len(suggested_qa_gen_profile['QA_generator_profiles'])), profiles_to_process)
                                
                                for profile_idx, profile_index in enumerate(selected_profile_indices):
                                    print(f"\n[LOGGING] Entering profile loop - iteration {profile_idx + 1}/{profiles_to_process}")
                                    print(f"\nDocument: {doc_name} | Profile {profile_idx + 1}/{profiles_to_process}")
                                    
                                    try:
                                        # Extract profile dynamically based on what dimensions exist
                                        profile_data = suggested_qa_gen_profile['QA_generator_profiles'][profile_index]
                                        profile_char = {}
                                        
                                        # Get all dimensions from the profile (except reason_for_profile)
                                        for key, value in profile_data.items():
                                            if key != 'reason_for_profile':
                                                # Store with original case for lookup, but also keep track of the key
                                                profile_char[key] = value
                                        
                                        # Validate that we have at least some dimensions
                                        if not profile_char:
                                            print(f"Warning: No valid dimensions found in profile {profile_index}, skipping...")
                                            overall_progress += 1
                                            continue
                                        
                                        # Create display string from available dimensions
                                        profile_display = " - ".join([f"{k}: {v}" for k, v in profile_char.items()])
                                        print(f"Profile: {profile_display}")
                                        
                                        print(f"[LOGGING] About to call qa_gen")
                                        syn_qa = qa_gen(aggregated_indices_text, QA_gen_profiles_json, profile_char, model_1)
                                        print(f"[LOGGING] Completed qa_gen")
                                        
                                        text_to_be_reviewed = {
                                            'distilled context:': aggregated_indices_text,
                                            'question': syn_qa['question']['question'],
                                            'answer': syn_qa['answer']['answer']
                                        }
                                        
                                        result_string = ""
                                        for key, value in text_to_be_reviewed.items():
                                            result_string += f"{key}: {value},\\n\\n "
                                        
                                        print(f"[LOGGING] About to call review_text")
                                        decision_of_review, reason_of_review = review_text(result_string, model_1)
                                        print(f"[LOGGING] Completed review_text")
                                        print(f"Review decision: {decision_of_review}")
                                        
                                        if "APPROVED" in decision_of_review:
                                            benchmark_entry = {
                                                'source_document': doc_name,
                                                'source_document_id': doc_id,
                                                'big chunk index:': big_chunk_index,
                                                'big chunk content:': chunk_text,
                                                'merged_chunk_ids': big_chunk['chunk_ids'],
                                                'chunk_count': big_chunk['chunk_count'],
                                                'clue index:': clue_index,
                                                'extended clue:': extended_clue,
                                                'retrieved contexts:': retrieved_contexts,
                                                'distilled context:': aggregated_indices_text,
                                                'qa gen profile index:': profile_index,
                                                'qa gen profile:': profile_char,
                                                'qa:': syn_qa,
                                                'decision of review:': decision_of_review,
                                                'reason of review:': reason_of_review
                                            }
                                            
                                            benchmark.append(benchmark_entry)
                                            print(f"✓ Added Q&A to benchmark (Total: {len(benchmark)})")
                                            
                                            # Save incrementally if output file is provided
                                            if output_file:
                                                if save_qa_incrementally(benchmark_entry, output_file):
                                                    print(f"✓ Saved Q&A incrementally to {output_file}")
                                                else:
                                                    print(f"⚠ Failed to save Q&A incrementally, but continuing...")
                                        
                                        print(f"&&& Overall Progress: {overall_progress}/{total_expected}")
                                        overall_progress += 1
                                        
                                    except Exception as e:
                                        print(f"[LOGGING] Error in profile loop: {e}")
                                        print(f"Error in profile loop: {e}")
                                        overall_progress += 1
                                        continue
                                        
                            except Exception as e:
                                print(f"[LOGGING] Error in clue loop: {e}")
                                print(f"Error in clue loop: {e}")
                                overall_progress += profiles_to_process
                                continue
                                
                    except Exception as e:
                        print(f"[LOGGING] Error in chunk loop: {e}")
                        print(f"Error in chunk loop: {e}")
                        overall_progress += clue_index_up * profile_index_up
                        continue
                
                print(f"\nCompleted processing document: {doc_name}")
                print(f"Generated {sum(1 for item in benchmark if item.get('source_document') == doc_name)} Q&As for this document")
                
            except Exception as e:
                print(f"[LOGGING] Error processing document {doc_name}: {e}")
                print(f"Error processing document {doc_name}: {e}")
                overall_progress += chunk_index_up * clue_index_up * profile_index_up
                continue
        
        print(f"\n{'='*80}")
        print(f"BENCHMARK GENERATION COMPLETE")
        print(f"Total Q&As generated: {len(benchmark)}")
        print(f"Documents processed: {docs_to_process}")
        print(f"{'='*80}")
        
        print(f"[LOGGING] Exiting main_benchmark_gen_vertex_search function successfully")
        return benchmark
        
    except Exception as e:
        print(f"[LOGGING] Unexpected error in main_benchmark_gen_vertex_search: {e}")
        print(f"An unexpected error occurred: {e}")
        return benchmark



def main():
    """Main function to run the Auto RAG Eval benchmark generation"""
    parser = argparse.ArgumentParser(description='Auto RAG Eval: A Novel Benchmark Creation Tool')
    parser.add_argument('--project-id', type=str, help='Google Cloud Project ID (overrides .env)')
    parser.add_argument('--location', type=str, help='Google Cloud Location (overrides .env)')
    parser.add_argument('--data-store-id', type=str, help='Vertex AI Search data store ID (overrides .env)')
    parser.add_argument('--docs', type=int, default=2, help='Number of documents to process')
    parser.add_argument('--chunks', type=int, default=2, help='Number of chunks per document')
    parser.add_argument('--clues', type=int, default=2, help='Number of clues per chunk')
    parser.add_argument('--profiles', type=int, default=2, help='Number of profiles per clue')
    parser.add_argument('--chunks-to-merge', type=int, default=3, help='Number of chunks to merge into bigger chunks')
    parser.add_argument('--output-file', type=str, default='benchmark.json', help='Output JSON filename')
    parser.add_argument('--qa-profiles-file', type=str, default=None, help='QA profiles JSON file path (default: qa_profiles.json in script directory)')
    parser.add_argument('--llm-model', type=str, default="gemini-2.0-flash", help='LLM model to use (default: gemini-2.0-flash)')
    parser.add_argument('--top-k-chunks', type=int, default=3, help='Number of top chunks to retrieve (default: 3)')
    parser.add_argument('--neighbour-chunks', type=int, default=0, help='Number of neighboring chunks to include (default: 0)')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum retry attempts for API calls (default: 3)')

    args = parser.parse_args()
    
    # Update global variables if provided (command line overrides .env)
    global PROJECT_ID, LOCATION, DATA_STORE_ID, TOP_K_CHUNKS, NEIGHBOUR_CHUNKS, MAX_RETRIES
    
    if args.project_id:
        PROJECT_ID = args.project_id
    if args.location:
        LOCATION = args.location
    if args.data_store_id:
        DATA_STORE_ID = args.data_store_id
    
    TOP_K_CHUNKS = args.top_k_chunks
    NEIGHBOUR_CHUNKS = args.neighbour_chunks
    MAX_RETRIES = args.max_retries
    
    # Initialize clients
    initialize_clients()
    
    # Load QA profiles with optional custom path
    global QA_gen_profiles
    QA_gen_profiles = load_qa_profiles(args.qa_profiles_file)
    
    # Print configuration source
    print("=== Auto RAG Eval Configuration ===")
    print(f"PROJECT_ID: {PROJECT_ID}")
    print(f"LOCATION: {LOCATION}")
    print(f"DATA_STORE_ID: {DATA_STORE_ID}")
    print("Configuration loaded from .env file (can be overridden by command-line arguments)")
    if args.qa_profiles_file:
        print(f"QA Profiles file specified: {args.qa_profiles_file}")
    else:
        print(f"QA Profiles file: {QA_PROFILES_FILE} (default location)")
    print("================================\n")
    
    # Run benchmark generation
    print("Starting Auto RAG Eval benchmark generation...")
    benchmark = main_benchmark_gen_vertex_search(
        doc_index_up=args.docs,
        chunk_index_up=args.chunks,
        clue_index_up=args.clues,
        profile_index_up=args.profiles,
        chunks_to_merge=args.chunks_to_merge,
        output_file=args.output_file,
        llm_model=args.llm_model
    )
    
    # Final processing of the benchmark
    if benchmark:
        # If we didn't save incrementally, save now
        if args.output_file:
            # Check if file already exists with incremental saves
            try:
                with open(args.output_file, 'r') as f:
                    existing_data = json.load(f)
                if len(existing_data) > 0:
                    print(f"\nBenchmark already saved incrementally to {args.output_file}")
                    print(f"Total Q&As saved: {len(existing_data)}")
                    # Display results as DataFrame
                    df = pd.json_normalize(existing_data)
                    print("\nGenerated Benchmark:")
                    print(df)
                else:
                    # File exists but empty, save the benchmark
                    json_data = convert_list_to_json(benchmark, args.output_file)
                    with open(args.output_file, 'w') as f:
                        json.dump(json_data, f, indent=4)
                    print(f"Benchmark saved to {args.output_file}")
            except (FileNotFoundError, json.JSONDecodeError):
                # File doesn't exist or is invalid, save the benchmark
                json_data = convert_list_to_json(benchmark, args.output_file)
                with open(args.output_file, 'w') as f:
                    json.dump(json_data, f, indent=4)
                print(f"Benchmark saved to {args.output_file}")
                # Display results as DataFrame
                df = pd.json_normalize(json_data)
                print("\nGenerated Benchmark:")
                print(df)
    else:
        print("No benchmark data generated.")


if __name__ == "__main__":
    main()