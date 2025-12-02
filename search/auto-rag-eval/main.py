
import os
import argparse
import random
import json
from dotenv import load_dotenv
from google.api_core.exceptions import InternalServerError, RetryError
import time

# Import local modules
import utils
import vertex_search_utils
import llm_utils

def main():
    parser = argparse.ArgumentParser(description="Auto RAG Eval: Automated Benchmark Generation")
    parser.add_argument("--project-id", help="Google Cloud Project ID")
    parser.add_argument("--location", help="GCP Region")
    parser.add_argument("--data-store-id", help="Vertex AI Search Data Store ID")
    parser.add_argument("--docs", type=int, default=2, help="Number of documents to process")
    parser.add_argument("--chunks", type=int, default=2, help="Number of chunks per document")
    parser.add_argument("--clues", type=int, default=2, help="Number of clues per chunk")
    parser.add_argument("--profiles", type=int, default=2, help="Number of Q&A profiles per clue")
    parser.add_argument("--chunks-to-merge", type=int, default=3, help="Number of chunks to merge")
    parser.add_argument("--output-file", default="benchmark.json", help="Output JSON filename")
    parser.add_argument("--qa-profiles-file", default="qa_profiles.json", help="QA profiles JSON file path")
    parser.add_argument("--llm-model", default="gemini-2.0-flash", help="LLM model to use")
    parser.add_argument("--top-k-chunks", type=int, default=3, help="Top K chunks for retrieval")
    parser.add_argument("--neighbour-chunks", type=int, default=0, help="Number of neighboring chunks")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum retry attempts")

    args = parser.parse_args()

    load_dotenv()
    project_id = args.project_id or os.getenv("PROJECT_ID")
    location = args.location or os.getenv("LOCATION", "us-central1")
    data_store_id = args.data_store_id or os.getenv("DATA_STORE_ID")

    if not project_id or not data_store_id:
        print("Error: Project ID and Data Store ID must be provided via arguments or .env file.")
        return

    # Download qa_profiles.json if missing
    if not os.path.exists(args.qa_profiles_file):
        print(f"{args.qa_profiles_file} not found. Attempting to download from GCS...")
        # In a real scenario, we would have the bucket name here.
        # For now, we'll assume it's provided or skip if not available.
        bucket_name = os.getenv("GCS_BUCKET_NAME", "github-repo")
        source_blob_name = f"search/auto-rag-eval/{args.qa_profiles_file}"
        if not utils.download_from_gcs(bucket_name, source_blob_name, args.qa_profiles_file):
            print("Failed to download qa_profiles.json. Using default profiles.")
            # Fallback to default profiles if needed, or exit
            return

    with open(args.qa_profiles_file, 'r') as f:
        qa_profiles_data = json.load(f)

    client = llm_utils.get_client(project_id, location)

    print(f"[LOGGING] Starting Auto RAG Eval with {args.docs} documents...")

    try:
        documents = vertex_search_utils.list_documents_in_datastore(project_id, location, data_store_id)
        if not documents:
            print("No documents found in data store.")
            return

        selected_docs = random.sample(documents, min(len(documents), args.docs))

        for doc in selected_docs:
            print(f"[LOGGING] Processing document: {doc['id']}")
            chunks = vertex_search_utils.list_chunks_for_document(doc['id'], project_id, location, data_store_id)
            if not chunks:
                continue

            bigger_chunks = vertex_search_utils.merge_chunks_into_bigger_chunks(chunks, args.chunks_to_merge)
            selected_chunks = random.sample(bigger_chunks, min(len(bigger_chunks), args.chunks))

            for chunk in selected_chunks:
                try:
                    clues_response = llm_utils.clue_generator(chunk['content'], client, args.llm_model)
                    selected_clues = random.sample(clues_response.questions, min(len(clues_response.questions), args.clues))

                    for clue in selected_clues:
                        # Context enhancement and search
                        target_info = llm_utils.targeted_information_seeking(clue.question, client, args.llm_model)
                        search_results = vertex_search_utils.search_with_chunk_augmentation(
                            target_info.original_question, project_id, location, data_store_id, args.top_k_chunks, args.neighbour_chunks
                        )

                        if not search_results:
                            continue

                        # Use first result's augmented content as context for simplicity in this refactor
                        context = search_results[0]['augmented_content']

                        # Generate Q&A pairs based on profiles
                        try:
                            # For simplicity, we'll randomly select profiles from the loaded data
                            # In a real scenario, we might use LLM to suggest profiles first
                            for _ in range(args.profiles):
                                # Randomly construct a profile from available dimensions
                                profile = {}
                                for dimension, details in qa_profiles_data['parameters'].items():
                                    value_name = random.choice(list(details['values'].keys()))
                                    profile[dimension] = details['values'][value_name]
                                    profile[dimension]['name'] = value_name

                                qa_pair = llm_utils.generate_qa_pair(context, profile, client, args.llm_model)

                                # Review
                                # Simplified review: just use one critic for now
                                review = llm_utils.review_qa_pair(qa_pair, context, "Analyst", client, args.llm_model)

                                if review.decision == "APPROVED":
                                    benchmark_entry = {
                                        'distilled context:': context,
                                        'qa gen profile:': profile,
                                        'qa:': {
                                            'question': {'question': qa_pair.question},
                                            'answer': {'answer': qa_pair.answer}
                                        }
                                    }
                                    utils.save_qa_incrementally(benchmark_entry, args.output_file)
                        except KeyError as ke:
                            print(f"[LOGGING] KeyError during profile generation: {ke}")
                            print(f"[LOGGING] qa_profiles_data keys: {qa_profiles_data.keys()}")
                            continue
                except Exception as e:
                    print(f"[LOGGING] Error processing chunk: {e}")
                    continue

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
