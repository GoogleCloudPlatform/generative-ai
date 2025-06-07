import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent

# API Keys and secrets
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
KAGGLE_USERNAME = os.getenv("KAGGLE_USERNAME")
KAGGLE_KEY = os.getenv("KAGGLE_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# LLM Configuration
LLM_CONFIG = {
    "provider": os.getenv("LLM_PROVIDER", "gemini"),  # gemini or vertex
    "model": os.getenv("LLM_MODEL", "gemini-1.5-pro"),
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "8192")),
    "top_p": float(os.getenv("LLM_TOP_P", "0.95")),
    "top_k": int(os.getenv("LLM_TOP_K", "40")),
}

# Tool configurations
SEARCH_CONFIG = {
    "provider": os.getenv("SEARCH_PROVIDER", "serpapi"),
    "max_results": int(os.getenv("SEARCH_MAX_RESULTS", "10")),
    "timeout": int(os.getenv("SEARCH_TIMEOUT", "30")),
}

DATASET_CONFIG = {
    "sources": ["kaggle", "huggingface", "github"],
    "max_results_per_source": int(os.getenv("DATASET_MAX_RESULTS", "5")),
    "timeout": int(os.getenv("DATASET_TIMEOUT", "30")),
}

# Workflow configurations
WORKFLOW_CONFIG = {
    "max_iterations": int(os.getenv("WORKFLOW_MAX_ITERATIONS", "3")),
    "validation_threshold": float(os.getenv("VALIDATION_THRESHOLD", "0.7")),
}

# API configurations
API_CONFIG = {
    "host": os.getenv("API_HOST", "0.0.0.0"),
    "port": int(os.getenv("API_PORT", "8000")),
    "debug": os.getenv("API_DEBUG", "False").lower() == "true",
}

# Monitoring configurations
MONITORING_CONFIG = {
    "enabled": False,
    "langfuse_host": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
}

# Logging configurations
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "app.log")
