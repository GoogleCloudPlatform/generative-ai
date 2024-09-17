# LlamaIndex Advanced Agentic RAG Implementation

## Overview

This project implements an advanced Retrieval-Augmented Generation (RAG) system using LlamaIndex and Google Cloud Vertex AI. It primarily focuses on rapid prototyping and experimentation of different combinations of indexing strategies, retrieval algorithms, and LLMs in order to attain the best performing combination for your problem. It covers RAG design, indexing, retrieval, evaluation metrics, and deployment on Google Cloud, emphasizing rapid experimentation and evaluation. It features a FastAPI backend for query processing and a Streamlit frontend for user interaction. The system leverages Google Gemini models for natural language processing and Vertex AI Vector Search for efficient document retrieval.

## Authors

- Sagar Kewalramani (`saaagesh`)
- Ken H Lee (`kenleejr`)

## Architecture

![Architecture Diagram](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/llamaindex-rag/LlamaIndex_Architecture.png)

_The architecture demonstrates a comprehensive flow from data ingestion to serving, incorporating various Google Cloud services to handle different aspects of the RAG system. It emphasizes the use of Vertex AI for key AI/ML components such as embeddings, vector storage, and language model inference. The system is designed to handle document processing, text embedding, efficient storage and retrieval, and serving of AI-powered results, with additional components for evaluation and monitoring._

## Key Features

- **Advanced RAG Techniques**: Implements various retrieval strategies including auto-merging, parent retrieval, and baseline approaches.
- **Flexible LLM Integration**: Supports multiple Gemini models (`gemini-1.5-pro`, `gemini-1.5-flash`) and Claude models (`claude-3.5-sonnet`) with configurable parameters.
- **Vector Search**: Utilizes Vertex AI Vector Search for efficient document indexing and retrieval.
- **Firestore**: Utilizes Firestore for document retrieval and auxiliary retrieval techniques
- **Document AI Integration**: Incorporates Google Cloud Document AI for processing and parsing various document formats.
- **Evaluation Metrics**: Includes built-in evaluation using metrics like answer relevancy, faithfulness, and context relevancy.
- **Interactive UI**: Features a Streamlit-based chat interface with real-time metric display and retrieved document information.

## Demonstration

### Chat Interface

![QAChatbot](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/llamaindex-rag/QnA_Rag_v3.gif)

### Evaluation Metrics

![Eval](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/llamaindex-rag/Batch_RAG_EVAL_v3.gif)

## Components

### Backend (FastAPI)

- `run_parse_embed_index.py`: Handles document indexing and vector store creation.
- `index_manager.py`: Implements the core RAG logic, including retrieval strategies and query processing.
- `docai_parser.py`: Integrates with Google's Document AI for document parsing.
- `main.py`: FastAPI application serving as the backend API.

### Frontend (Streamlit)

- `1_🗄️ Data Sources.py`: Page for choosing vector search indices and docstore collections for retrieval
- `2_🖊️ Prompts.py`: Page for changing relevant prompts for the RAG pipeline
- `3_💬 Q&A_Chatbot.py`: Streamlit application providing an interactive chat interface and configuration options to experiment with RAG.
- `4_📊 Batch Evaluations.py`: Batch evaluation page for kicking off evaluations against a user-uploaded csv of ground truth questions and answers.

## Setup and Configuration

1. Ensure you have the necessary Google Cloud credentials and project setup.
2. Install required dependencies (requirements.txt to be added).
3. Configure the `config.yaml` file with your project-specific settings:
   - Project ID
   - Location
   - Bucket names
   - Model names
   - Vector index and endpoint names

### Prerequisites

- Access to a VM machine (recommended for local indexing)
- Docker installed
- Google Cloud SDK installed and configured

## Steps

1. Clone the repository:

```bash
git clone https://github.com/GoogleCloudPlatform/generative-ai
cd gemini/sample-apps/llamaindex-rag
```

2. Set up the environment:

```bash
conda create -n llamaindex-rag python=3.10
poetry install
```

3. Configure the application:
   - Modify the parameters in `common/config.yaml` as needed
4. Run the indexing job:

```bash
export PYTHONPATH="." (in the parent directory llamaindex-rag)
python src/indexing/run_parse_embed_index.py
```

5. Build and deploy the FastAPI application:

```sh
export PROJECT_ID=your-project-id
export SERVICE_ACCOUNT=your-service-account@your-project.iam.gserviceaccount.com
docker build -t fastapi-llamaindex-rag .
docker tag fastapi-llamaindex-rag gcr.io/${PROJECT_ID}/fastapi-llamaindex-rag
docker push gcr.io/${PROJECT_ID}/fastapi-llamaindex-rag
gcloud run deploy fastapi-llamaindex-rag \
--image gcr.io/${PROJECT_ID}/fastapi-llamaindex-rag \
--platform managed \
--region us-central1 \
--allow-unauthenticated \
--port 8080 \
--set-env-vars=CONFIG_PATH=/app/common/config.yaml \
--service-account=${SERVICE_ACCOUNT} \
--cpu 2 \
--memory 4Gi \
--max-instances 1
```

OR run locally:

```sh
python backend/app/main.py
```

6. Build and deploy the Streamlit UI:

```sh
docker build -f ui/Dockerfile -t fastapi-streamlit-app .
docker tag fastapi-streamlit-app gcr.io/${PROJECT_ID}/fastapi-streamlit-app
docker push gcr.io/${PROJECT_ID}/fastapi-streamlit-app
gcloud run deploy fastapi-streamlit-app \
--image gcr.io/${PROJECT_ID}/fastapi-streamlit-app \
--platform managed \
--region us-central1 \
--allow-unauthenticated \
--port 8080 \
--service-account=${SERVICE_ACCOUNT} \
--cpu 2 \
--memory 4Gi \
--max-instances 1
```

OR run locally:

```sh
streamlit run ui/🏠 Home.py
```

Note: Replace `your-project-id` and `your-service-account@your-project.iam.gserviceaccount.com` with your actual Google Cloud project ID and service account email.

## Advanced Features

- **HyDE (Hypothetical Document Embeddings)**: Enhances retrieval by generating hypothetical relevant documents.
- **Response Refinement**: Improves answer quality through iterative refinement.
- **Node Reranking**: Uses LLM to rerank retrieved documents for better relevance.
- **Hierarchical Retrieval**: Supports hierarchical document structures for more contextual retrieval.

## Evaluation

The system provides real-time evaluation metrics for each query:

- Answer Relevancy
- Faithfulness
- Context Relevancy

These metrics help in assessing the quality and reliability of the generated responses.

## Customization

- Extend retrieval strategies in `index_manager.py` for custom retrieval methods.
- Adjust Document AI processing in `docai_parser.py` for specific document handling needs.

## Future Enhancements

- Integration with more LLM models
- Enhanced logging and monitoring
- Support for multi-modal inputs
- Improved caching mechanisms for faster responses

## Contributing

Contributions to improve the system are welcome. Please follow the standard GitHub pull request process to submit your changes.

## License

This project is licensed under the standard Google Apache-2.0 license.

## Get in Touch

Please file any GitHub issues if you have any questions or suggestions.

- Sagar Kewalramani (`saaagesh`)
- Ken H Lee (`kenleejr`)
