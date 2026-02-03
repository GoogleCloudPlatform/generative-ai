# Auto RAG Eval: Automated Benchmark Generation for RAG Systems

| Authors |
| --- |
| [Pouya Omran](https://github.com/PouyaOmran) |
| [Tanya Dixit](https://github.com/coderkhaleesi) |
| [Jingyi Wang](https://github.com/Jingyi-Wang-jessie) |

## TL;DR - Quick Start

```bash
# 1. Install requirements
pip install -r requirements.txt

# 2. Download required files from Google Cloud Storage
gcloud storage cp gs://github-repo/search/auto-rag-eval/qa_profiles.json .

# 3. Set up environment
# Edit .env with your values:
# - PROJECT_ID=your-gcp-project-id
# - LOCATION=us-central1
# - DATA_STORE_ID=your-vertex-ai-search-datastore-id

# 4. Authenticate with Google Cloud
gcloud auth application-default login

# 5. Generate benchmark
python main.py --docs 2 --chunks 2 --clues 2 --profiles 2

# 6. (Optional) Transform benchmark for evaluation frameworks
python transform_benchmark.py benchmark.json converted_benchmark.json
```

That's it! Your benchmark Q&A pairs will be saved to `benchmark.json`.

## What is it?

Auto RAG Eval is an automated benchmark generation tool for evaluating Retrieval-Augmented Generation (RAG) systems.
It creates high-quality question-answer pairs from your document corpus using Google Cloud's Vertex AI Search and Gemini models.

The primary component of this solution is the **Benchmark Generator** (`main.py`), which creates the Q&A pairs from your documents in Vertex AI Search.

A secondary utility, the **Benchmark Transformer** (`transform_benchmark.py`), is also provided. This simple script can be used to convert the generated benchmark into a format compatible with evaluation frameworks like Google's Agent Development Kit (ADK).

## Why do we need this solution?

### The Challenge
- **Manual Benchmark Creation is Time-Consuming**: Creating quality benchmarks for RAG systems manually can take weeks or months
- **Coverage Gaps**: Human-created benchmarks often miss edge cases and don't comprehensively cover the document corpus
- **Scalability Issues**: As document stores grow, maintaining relevant benchmarks becomes increasingly difficult
- **Evaluation Consistency**: Without standardized benchmarks, it's hard to consistently evaluate RAG system performance

### The Solution
Auto RAG Eval addresses these challenges by:
- **Automating Benchmark Generation**: Creates hundreds of Q&A pairs in hours instead of weeks
- **Ensuring Comprehensive Coverage**: Systematically samples documents and chunks to cover the entire corpus
- **Multi-Stage Quality Control**: Uses multiple AI agents to review and validate each Q&A pair
- **Scalable Architecture**: Works with any size Vertex AI Search data store
- **Format Flexibility**: Transforms benchmarks into various formats for different evaluation frameworks

## How to use this solution

### Prerequisites

1.  **Google Cloud Project** with the following APIs enabled:
    -   Vertex AI API
    -   Discovery Engine API (for Vertex AI Search)
    -   Cloud Storage API

2.  **Authentication**:
    ```bash
    # Set up Application Default Credentials
    gcloud auth application-default login
    ```

3.  **Vertex AI Search Data Store**:
    -   Create a data store in Vertex AI Search
    -   Ingest your documents into the data store
    -   Note the data store ID
    -   Detailed instructions on creating a data store in Google Cloud Console:
        1.  **Navigate to AI Applications** in the Google Cloud Console
        2.  **Create a new data store** for your application
        3.  **Configure the parser settings**:
            -   Set the parser to either **Digital Parser** or **Layout Parser**
        4.  **Enable Advanced Chunking Configuration**:
            -   ✓ Tick **"Include ancestor headings in chunks"**
            -   Keep all other settings at their default values
        5.  **Ingest your free text documents** into the data store
        6.  **Copy the DATA_STORE_ID** from the console
        7.  **Add the DATA_STORE_ID to your `.env` file**:
            DATA_STORE_ID=your-data-store-id

Upload the documents in exemplary_docs to the datastore from gs://github-repo/search/auto-rag-eval/

4.  **Python Environment**:
    ```bash
    # Install all required dependencies
    pip install -r requirements.txt
    ```

5.  **Required Files**:
    -   `qa_profiles.json`: Q&A generation profiles. Download it from Google Cloud Storage:
        ```bash
        gcloud storage cp gs://github-repo/search/auto-rag-eval/qa_profiles.json .
        ```
    -   `.env`: Environment configuration (create from `env_example`)

### Step 1: Configure Environment

Create a `.env` file based on `env_example`:

```bash
# Copy the example file
cp env_example .env

# Edit with your values
PROJECT_ID=your-gcp-project-id
LOCATION=us-central1
DATA_STORE_ID=your-data-store-id
```

### Step 2: Generate Benchmark

Run the benchmark generator with default settings:

```bash
python main.py
```

Or customize the generation parameters:

```bash
python main.py \
    --docs 5 \
    --chunks 3 \
    --clues 2 \
    --profiles 2 \
    --chunks-to-merge 3 \
    --output-file my_benchmark.json \
    --qa-profiles-file custom_profiles.json
```

**Parameters**:
-   `--project-id`: Override PROJECT_ID from .env file
-   `--location`: Override LOCATION from .env file
-   `--data-store-id`: Override DATA_STORE_ID from .env file
-   `--docs`: Number of documents to process (default: 2)
-   `--chunks`: Number of chunks per document (default: 2)
-   `--clues`: Number of clues per chunk (default: 2)
-   `--profiles`: Number of Q&A profiles per clue (default: 2)
-   `--chunks-to-merge`: Number of chunks to merge into bigger chunks (default: 3)
-   `--output-file`: Output JSON filename (default: benchmark.json)
-   `--qa-profiles-file`: Path to custom QA profiles JSON file (default: qa_profiles.json in script directory)
-   `--llm-model`: LLM model to use (default: gemini-3-flash-preview)
-   `--top-k-chunks`: Number of top chunks to retrieve during context search (default: 3)
-   `--neighbour-chunks`: Number of neighboring chunks to include for context (default: 0)
-   `--max-retries`: Maximum retry attempts for API calls (default: 3)

### Step 3: Transform Benchmark (Optional)

After generating your benchmark, you can optionally convert it for use with evaluation frameworks like the Agent Development Kit (ADK). You can use the standalone Python script.

```bash
python transform_benchmark.py benchmark.json converted_bench.json
```

The script accepts command-line arguments:
-   First argument: Input benchmark file path
-   Second argument: Output file path
-   Optional `--indent`: JSON indentation level (default: 2)

The transformer converts from Auto RAG Eval format:
```json
{
    "context": "...",
    "Q&A Gen Profile": {...},
    "Question": "...",
    "Answer": "..."
}
```

To ADK evaluation format:
```json
{
    "query": "...",
    "expected_tool_use": [],
    "reference": "..."
}
```

## Architecture Overview

### System Architecture

Auto RAG Eval follows a sophisticated multi-stage pipeline architecture that orchestrates various AI models and services to generate high-quality Q&A pairs:

```
┌─────────────────────────┐
│   Vertex AI Search      │
│   (Document Store)      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐     ┌─────────────────────┐
│  Document Selection     │────▶│  Chunk Processing   │
│  - List all documents   │     │  - Retrieve chunks  │
│  - Random sampling      │     │  - Merge chunks     │
└─────────────────────────┘     └──────────┬──────────┘
                                           │
                                           ▼
                                ┌─────────────────────┐
                                │   Clue Generation   │
                                │  - Identify topics  │
                                │  - Generate question│
                                └──────────┬──────────┘
                                           │
                                           ▼
┌─────────────────────────┐     ┌─────────────────────┐
│  Context Retrieval      │────▶│ Context Distillation│
│  - Search with clues    │     │  - Relevance filter │
│  - Find related chunks  │     │  - Extract focused  │
└─────────────────────────┘     │    content          │
                                └──────────┬──────────┘
                                           │
                                           ▼
┌─────────────────────────┐     ┌─────────────────────┐
│  Q&A Profile Generation │────▶│   Q&A Generation    │
│  - Analyze context      │     │  - Create Q&A pairs │
│  - Suggest profiles     │     │  - Self-contained   │
└─────────────────────────┘     └──────────┬──────────┘
                                           │
                                           ▼
┌─────────────────────────┐     ┌─────────────────────┐
│  Multi-Agent Review     │────▶│ Incremental Saving  │
│  - 3 AI critics         │     │  - Immediate save   │
│  - Consensus decision   │     │  - JSON output      │
└─────────────────────────┘     └─────────────────────┘
```

### Data Flow

The data flows through the pipeline as follows:

1.  **Input**: Vertex AI Search data store containing your documents
2.  **Processing**: Documents → Chunks → Clues → Retrieved Contexts → Distilled Context → Profiles → Q&As
3.  **Output**: JSON file with validated Q&A pairs

### Detailed Pipeline Stages

1.  **Document Selection**
    -   Lists all documents from Vertex AI Search data store
    -   Randomly selects specified number of documents
    -   Ensures diverse coverage of the corpus

2.  **Chunk Processing**
    -   Retrieves chunks for each selected document
    -   Merges consecutive chunks into bigger chunks for better context
    -   Default: merges 3 chunks together
    -   Randomly selects chunks for processing

3.  **Clue Generation**
    -   For each chunk, generates potential questions (clues)
    -   Uses Gemini model to identify key topics and concepts
    -   Ensures questions are answerable from the text

4.  **Context Retrieval**
    -   For each clue, searches for relevant contexts using Vertex AI Search
    -   Enhances the clue with hypothetical examples and descriptions
    -   Retrieves top-k most relevant chunks from the entire corpus
    -   Can include neighboring chunks for additional context

5.  **Context Distillation**
    -   Extracts only the most relevant portions from retrieved contexts
    -   Uses both individual block-level and overall document-level relevance assessment
    -   Filters out irrelevant information to create focused context
    -   Aggregates relevant text from multiple sources

6.  **Q&A Profile Generation**
    -   Analyzes the distilled context to suggest Q&A generation profiles
    -   Profiles vary by customizable dimensions from `qa_profiles.json`
    -   Default dimensions: Type, Persona, Scope, Difficulty
    -   Generates diverse profiles for comprehensive coverage

7.  **Q&A Generation**
    -   Creates question-answer pairs based on profiles and distilled context
    -   Ensures Q&As are self-contained and context-based
    -   Questions synthesize information across the entire context
    -   Answers are grounded only in the provided text

### Key Design Decisions

1.  **Incremental Processing**: Each Q&A is saved immediately upon approval, preventing data loss
2.  **Multi-Stage Relevance**: Both individual and aggregate relevance assessment ensures comprehensive context
3.  **Consensus-Based Review**: Multiple AI critics ensure high-quality output
4.  **Flexible Profiles**: Customizable Q&A dimensions via external JSON configuration
5.  **Retry Mechanisms**: Automatic retry with exponential backoff for API resilience
6.  **Progress Tracking**: Detailed logging with [LOGGING] prefix for monitoring

### API Integration Points

-   **Vertex AI Search**: Document listing, chunk retrieval, semantic search
-   **Gemini Models**: Clue generation, profile suggestion, Q&A generation, review
-   **Google Cloud Storage**: Optional for document storage
-   **Discovery Engine API**: Core search and retrieval functionality

### Key Features

-   **Fault Tolerance**: Automatic retry with exponential backoff for API failures
-   **Progress Tracking**: Detailed logging with [LOGGING] prefix
-   **Incremental Saving**: Each Q&A saved immediately upon approval
-   **Quality Control**: Multi-agent review system ensures high-quality outputs
-   **Diversity**: Generates varied Q&A types for comprehensive evaluation

## Example Data and Output

### Exemplary Documents

This repository includes a folder `exemplary_docs/` containing three PDF documents about Google AI agents:
-   `input_2_ai-responsibility-update-published-february-2025.pdf` - Google's AI responsibility update
-   `input_2_exec_guide_gen_ai.pdf` - Executive guide to generative AI
-   `input_2_google-about-generative-ai.pdf` - General information about Google's generative AI

These documents were ingested into a Vertex AI Search data store with the following settings:
-   **LLM feature enabled** for table and image annotation
-   **Layout parser option** enabled during ingestion time
-   The data store ID is configured in the `env example` file

### Generated Benchmark Files

From these exemplary documents, we have generated:
-   `benchmark.json` - The raw benchmark output from Auto RAG Eval containing 15 Q&A pairs
-   `converted_benchmark.json` - The transformed benchmark ready for evaluation frameworks

## Output Format

### Auto RAG Eval Benchmark Format (benchmark.json)
```json
[
    {
        "context": "The distilled context used for Q&A generation",
        "Q&A Gen Profile": {
            "type": "How-to",
            "persona": "The Expert",
            "scope": "Whole",
            "difficulty": "Hard"
        },
        "Question": "The generated question",
        "Answer": "The generated answer"
    }
]
```

### ADK Format (after transformation)
```json
[
    {
        "query": "The generated question",
        "expected_tool_use": [],
        "reference": "The generated answer"
    }
]
```

## Customizing Q&A Profiles

The `qa_profiles.json` file contains the configuration for Q&A generation. The updated script now supports flexible dimension handling:

### What You Can Customize:

1.  **Dimension Names**: You can rename dimensions (e.g., "Type" → "QuestionType", "Persona" → "AudienceLevel")
2.  **Number of Dimensions**: Add or remove dimensions as needed (minimum 1 dimension required)
3.  **Dimension Values**: Add, remove, or modify values within each dimension
4.  **Value Descriptions**: Customize descriptions for each value

### Structure Requirements:

The only requirement is maintaining this JSON structure:
```json
{
  "parameters": {
    "YourDimensionName": {
      "description": "Description of this dimension",
      "values": {
        "ValueName1": {"description": "Description of this value"},
        "ValueName2": {"description": "Description of this value"}
      }
    }
  }
}
```

### Example: Custom Profile with Different Dimensions

```json
{
  "parameters": {
    "Domain": {
      "description": "Subject area",
      "values": {
        "Technical": {"description": "Technical documentation"},
        "Business": {"description": "Business processes"}
      }
    }
  }
}
```

### Note

While RAG-Crusher employs an intelligent, LLM-infused methodology to automatically generate high-quality benchmarks, the
generated Q&A pairs should be treated with caution. Despite the multi-stage quality control and multi-agent review process,
the ultimate validity and accuracy of the generated benchmarks should be verified by human domain experts who are familiar with
the subject matter.
We recommend:

Having subject matter experts review the generated Q&A pairs before using them in production evaluations
Treating the generated benchmark as a starting point that requires human validation
Being particularly careful with answers related to critical, safety-sensitive, or highly specialized domains
Manually reviewing a representative sample of the generated pairs to ensure they meet your quality standards

The tool is designed to accelerate benchmark creation, not to replace human expertise and judgment.


### To customize profiles:
1.  Edit `qa_profiles.json` with your desired dimensions and values
2.  Run the benchmark generator - it will automatically adapt to your new structure
3.  The script will validate the structure and use whatever dimensions you provide

## Monitoring and Troubleshooting

### Logging
-   Look for `[LOGGING]` prefix in console output for detailed execution tracking
-   Each function entry/exit is logged
-   API retry attempts are logged with error details

### Common Issues

1.  **Authentication Errors**:
    ```bash
    gcloud auth application-default login
    ```

2.  **API Rate Limits**:
    -   Adjust delays in the code
    -   Reduce concurrent processing

3.  **Empty Benchmark**:
    -   Check data store ID is correct
    -   Verify documents are properly ingested
    -   Check API permissions

4.  **Memory Issues**:
    -   Process fewer documents at once
    -   Reduce chunk merge size

5.  **Missing qa_profiles.json**:
    -   The script will use default profiles if the file is missing
    -   Check that the file is in the same directory as the script
