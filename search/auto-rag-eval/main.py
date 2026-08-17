"""Command-line entry point for Auto RAG Eval benchmark generation."""  # noqa: INP001

from __future__ import annotations

import argparse
import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import llm_utils
import utils
import vertex_search_utils
from dotenv import load_dotenv
from google.api_core.exceptions import GoogleAPIError

if TYPE_CHECKING:
    from google import genai


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the benchmark generator."""
    parser = argparse.ArgumentParser(
        description="Auto RAG Eval: Automated Benchmark Generation"
    )
    parser.add_argument("--project-id", help="Google Cloud Project ID")
    parser.add_argument("--location", help="GCP Region")
    parser.add_argument(
        "--data-store-id", help="Vertex AI Agent Platform Data Store ID"
    )
    parser.add_argument(
        "--docs", type=int, default=2, help="Number of documents to process"
    )
    parser.add_argument(
        "--chunks", type=int, default=2, help="Number of chunks per document"
    )
    parser.add_argument(
        "--clues", type=int, default=2, help="Number of clues per chunk"
    )
    parser.add_argument(
        "--profiles", type=int, default=2, help="Number of Q&A profiles per clue"
    )
    parser.add_argument(
        "--chunks-to-merge", type=int, default=3, help="Number of chunks to merge"
    )
    parser.add_argument(
        "--output-file", default="benchmark.json", help="Output JSON filename"
    )
    parser.add_argument(
        "--qa-profiles-file",
        default="qa_profiles.json",
        help="QA profiles JSON file path",
    )
    parser.add_argument(
        "--llm-model", default="gemini-3.5-flash", help="LLM model to use"
    )
    parser.add_argument(
        "--top-k-chunks", type=int, default=3, help="Top K chunks for retrieval"
    )
    parser.add_argument(
        "--neighbour-chunks", type=int, default=0, help="Number of neighboring chunks"
    )
    parser.add_argument(
        "--max-retries", type=int, default=3, help="Maximum retry attempts"
    )
    return parser.parse_args()


@dataclass
class _PipelineContext:
    """Shared state threaded through the benchmark generation pipeline."""

    client: genai.Client
    args: argparse.Namespace
    rng: random.Random
    qa_profiles_data: dict[str, Any]
    store: vertex_search_utils.DataStoreConfig


def _build_random_profile(ctx: _PipelineContext) -> dict[str, Any]:
    """Construct a random Q&A profile from the available dimensions."""
    profile: dict[str, Any] = {}
    for dimension, details in ctx.qa_profiles_data["parameters"].items():
        value_name = ctx.rng.choice(list(details["values"].keys()))
        profile[dimension] = details["values"][value_name]
        profile[dimension]["name"] = value_name
    return profile


def _generate_qa_for_context(context: str, ctx: _PipelineContext) -> None:
    """Generate, review, and save Q&A pairs for a single context."""
    try:
        for _ in range(ctx.args.profiles):
            profile = _build_random_profile(ctx)
            qa_pair = llm_utils.generate_qa_pair(
                context, profile, ctx.client, ctx.args.llm_model
            )
            # Simplified review: just use one critic for now.
            review = llm_utils.review_qa_pair(
                qa_pair, context, "Analyst", ctx.client, ctx.args.llm_model
            )
            if review.decision == "APPROVED":
                benchmark_entry = {
                    "distilled context:": context,
                    "qa gen profile:": profile,
                    "qa:": {
                        "question": {"question": qa_pair.question},
                        "answer": {"answer": qa_pair.answer},
                    },
                }
                utils.save_qa_incrementally(benchmark_entry, ctx.args.output_file)
    except KeyError as ke:
        print(f"[LOGGING] KeyError during profile generation: {ke}")
        print(f"[LOGGING] qa_profiles_data keys: {ctx.qa_profiles_data.keys()}")


def _process_clue(clue: llm_utils.QuestionClue, ctx: _PipelineContext) -> None:
    """Enhance a clue, retrieve context, and generate Q&A pairs."""
    target_info = llm_utils.targeted_information_seeking(
        clue.question, ctx.client, ctx.args.llm_model
    )
    search_results = vertex_search_utils.search_with_chunk_augmentation(
        target_info.original_question,
        ctx.store,
        ctx.args.top_k_chunks,
        ctx.args.neighbour_chunks,
    )
    if not search_results:
        return

    # Use first result's augmented content as context for simplicity.
    context = search_results[0]["augmented_content"]
    _generate_qa_for_context(context, ctx)


def _process_chunk(chunk: dict[str, Any], ctx: _PipelineContext) -> None:
    """Generate clues for a chunk and process each of them."""
    try:
        clues_response = llm_utils.clue_generator(
            chunk["content"], ctx.client, ctx.args.llm_model
        )
        selected_clues = ctx.rng.sample(
            clues_response.questions,
            min(len(clues_response.questions), ctx.args.clues),
        )
        for clue in selected_clues:
            _process_clue(clue, ctx)
    except (GoogleAPIError, vertex_search_utils.DataStoreError) as e:
        print(f"[LOGGING] Error processing chunk: {e}")


def _process_document(doc: dict[str, Any], ctx: _PipelineContext) -> None:
    """List, merge, sample, and process the chunks of a single document."""
    print(f"[LOGGING] Processing document: {doc['id']}")
    chunks = vertex_search_utils.list_chunks_for_document(doc["id"], ctx.store)
    if not chunks:
        return

    bigger_chunks = vertex_search_utils.merge_chunks_into_bigger_chunks(
        chunks, ctx.args.chunks_to_merge
    )
    selected_chunks = ctx.rng.sample(
        bigger_chunks, min(len(bigger_chunks), ctx.args.chunks)
    )
    for chunk in selected_chunks:
        _process_chunk(chunk, ctx)


def main() -> None:
    """Run the Auto RAG Eval benchmark generation pipeline."""
    args = _parse_args()

    load_dotenv()
    project_id = args.project_id or os.getenv("PROJECT_ID")
    location = args.location or os.getenv("LOCATION", "us-central1")
    data_store_id = args.data_store_id or os.getenv("DATA_STORE_ID")

    if not project_id or not data_store_id:
        print(
            "Error: Project ID and Data Store ID must be provided via arguments or "
            ".env file."
        )
        return

    # Download qa_profiles.json if missing.
    profiles_path = Path(args.qa_profiles_file)
    if not profiles_path.exists():
        print(f"{args.qa_profiles_file} not found. Attempting to download from GCS...")
        bucket_name = os.getenv("GCS_BUCKET_NAME", "github-repo")
        source_blob_name = f"search/auto-rag-eval/{args.qa_profiles_file}"
        if not utils.download_from_gcs(
            bucket_name, source_blob_name, args.qa_profiles_file
        ):
            print("Failed to download qa_profiles.json. Using default profiles.")
            return

    with profiles_path.open() as f:
        qa_profiles_data = json.load(f)

    ctx = _PipelineContext(
        client=llm_utils.get_client(project_id, location),
        args=args,
        rng=random.SystemRandom(),
        qa_profiles_data=qa_profiles_data,
        store=vertex_search_utils.DataStoreConfig(
            project_id=project_id,
            location=location,
            data_store_id=data_store_id,
        ),
    )

    print(f"[LOGGING] Starting Auto RAG Eval with {args.docs} documents...")

    try:
        documents = vertex_search_utils.list_documents_in_datastore(ctx.store)
        if not documents:
            print("No documents found in data store.")
            return

        selected_docs = ctx.rng.sample(documents, min(len(documents), args.docs))
        for doc in selected_docs:
            _process_document(doc, ctx)
    except (GoogleAPIError, vertex_search_utils.DataStoreError) as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
