#!/usr/bin/env python3
"""General Invoice Processing Multi-Agent System

Domain-independent invoice processing pipeline with configurable validation rules.
Each agent produces intermediate artifacts stored in output/{case_id}/

Version: 1.1.1
Reference: reconstructed_rules_book.md

Usage:
    python general_invoice_agent.py --base-dir path/to/invoices
    python general_invoice_agent.py --case path/to/single/case
    python general_invoice_agent.py --base-dir path/to/invoices --config config.json

Output:
    All outputs are saved in the SCRIPT DIRECTORY (not current working directory):
    general-invoice-processing-agent-gym/
    └── output/
        └── {case_id}/
            ├── 01_classification.json
            ├── 02_extraction.json
            ├── ...
            └── Postprocessing_Data.json

Note:
    - Outputs go to script's folder regardless of where you run it from
    - Config files are resolved relative to script directory if not absolute
    - .env file is loaded from script directory first
"""

import argparse
import json
import os
import re
import sys
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, ClassVar, Literal

# Third-party imports
try:
    import pdfplumber
    from dotenv import load_dotenv
    from google.cloud import aiplatform
    from pydantic import BaseModel, Field
    from vertexai.generative_models import (
        GenerationConfig,
        GenerativeModel,
        Part,
    )
except ImportError:
    print("Error: Missing required package. Install with:")
    print("pip install google-cloud-aiplatform pydantic pdfplumber python-dotenv")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Resolve paths: acting/ -> shared_libraries/ -> invoice_processing/ (package root with data/ inside)
SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_PKG_DIR = SCRIPT_DIR.parent.parent
OUTPUT_BASE_DIR = AGENT_PKG_DIR / "data" / "agent_output"

# Recipe root for .env resolution (holds .env / .env.example beside the package)
PROJECT_ROOT = AGENT_PKG_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()  # Fallback to default behavior

# Magic-value constants
_MIN_PDF_CONTENT_LENGTH = 50
_ABN_EXPECTED_LENGTH = 11


@dataclass
class _GCPConfig:
    """Mutable container for Google Cloud configuration (lazy-initialized).

    Model names and location default from environment variables so they are
    never hardcoded in source; the literals are only last-resort fallbacks.
    `_ensure_gcp_initialized()` re-reads them at first use to pick up env vars
    that Agent Engine sets after import.
    """

    PROJECT_ID: str | None = None
    LOCATION: str = field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    )
    GEMINI_FLASH_MODEL: str = field(
        default_factory=lambda: os.getenv("MODEL_NAME", "gemini-3.5-flash")
    )
    GEMINI_PRO_MODEL: str = field(
        default_factory=lambda: os.getenv("GEMINI_PRO_MODEL", "gemini-3.5-pro")
    )
    API_CALL_DELAY_SECONDS: float = field(
        default_factory=lambda: float(os.getenv("API_CALL_DELAY_SECONDS", "1.0"))
    )
    initialized: bool = False


_gcp_config = _GCPConfig()


def _ensure_gcp_initialized():
    """Lazy-initialize GCP/Vertex AI on first use (not at import time).

    Agent Engine sets env vars after module import, so we must defer.
    """
    if _gcp_config.initialized:
        return
    _gcp_config.PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
    _gcp_config.LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    _gcp_config.GEMINI_FLASH_MODEL = os.getenv("MODEL_NAME", "gemini-3.5-flash")
    _gcp_config.GEMINI_PRO_MODEL = os.getenv("GEMINI_PRO_MODEL", "gemini-3.5-pro")
    _gcp_config.API_CALL_DELAY_SECONDS = float(
        os.getenv("API_CALL_DELAY_SECONDS", "1.0")
    )
    if not _gcp_config.PROJECT_ID:
        print("Warning: PROJECT_ID not found in environment")
        print("Set it in .env file or export PROJECT_ID=your-gcp-project-id")
    else:
        aiplatform.init(project=_gcp_config.PROJECT_ID, location=_gcp_config.LOCATION)
    _gcp_config.initialized = True


# Default configuration - can be overridden via config file
DEFAULT_CONFIG = {
    # Organization names for customer verification
    "organization_names": ["ACME Corp", "ACME Corporation", "ACME Ltd"],
    # Tax settings
    "default_tax_rate": 0.10,  # 10%
    "tax_rates_by_currency": {
        "AUD": 0.10,
        "NZD": 0.15,
        "USD": 0.00,
        "EUR": 0.20,
    },
    # Validation settings
    "require_work_authorization": False,
    "waf_exempt_work_types": ["PREVENTATIVE", "CLEANING"],
    "waf_exempt_vendors": [],
    # PO validation
    "require_purchase_order": False,
    "valid_po_prefixes": ["PO", "WO", "PR"],
    # Duplicate detection
    "duplicate_check_enabled": False,
    "duplicate_check_type": "none",  # "none", "file", "database", "api"
    # Tolerances
    "balance_tolerance": 0.02,
    "line_sum_tolerance": 1.00,
    "hours_tolerance": 0.5,
    # Tax ID validation
    "validate_tax_id_checksum": True,
    "tax_id_format": "ABN",  # "ABN", "VAT", "EIN", "NONE"
}

# Module-level mutable containers for config and metrics
_config_store: dict[str, Any] = {"CONFIG": DEFAULT_CONFIG.copy()}

_metrics_store: dict[str, Any] = {
    "METRICS": {
        "llm_calls": 0,
        "total_tokens": {"prompt": 0, "completion": 0},
        "total_cost_usd": 0.0,
        "agent_breakdown": [],
    }
}


def _get_config() -> dict:
    """Return the current CONFIG dict."""
    return _config_store["CONFIG"]


def _get_metrics() -> dict:
    """Return the current METRICS dict."""
    return _metrics_store["METRICS"]


# Pricing per 1M tokens
MODEL_PRICING = {
    "gemini-3.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-3.5-pro": {"input": 1.25, "output": 10.00},
}


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================


class DocumentContent(BaseModel):
    """Identifies document types present in a file"""

    has_invoice: bool = False
    has_work_authorization: bool = False
    invoice_count: int = 0
    reasoning: str = ""


class InvoiceLineItem(BaseModel):
    """Single line item from invoice"""

    description: str
    quantity: float | None = None
    unit_price: float | None = None
    amount_ex_tax: float | None = None
    tax_code: str | None = "TAX"
    tax_amount: float | None = None
    amount_inc_tax: float | None = None


class InvoiceExtraction(BaseModel):
    """Extracted invoice data"""

    invoice_number: str | None = "UNKNOWN"
    invoice_date: str | None = ""
    invoice_total_inc_tax: float | None = 0.0
    invoice_total_ex_tax: float | None = 0.0
    tax_amount: float | None = 0.0
    vendor_tax_id: str | None = None
    vendor_name: str | None = "UNKNOWN"
    customer_name: str | None = None
    currency: str | None = "AUD"
    line_items: list[InvoiceLineItem] | None = []


class WorkAuthorizationExtraction(BaseModel):
    """Extracted work authorization data"""

    reference_number: str | None = None
    site_name: str | None = None
    authorized_hours: float | None = None
    work_description: str | None = None
    technician_name: str | None = None
    date: str | None = None


class WorkTypeClassification(BaseModel):
    """LLM response for work type classification"""

    work_type: Literal["REPAIRS", "PREVENTATIVE", "CLEANING", "EMERGENCY"] = Field(
        description="The work type category"
    )
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class ItemCodeClassification(BaseModel):
    """LLM response for item code classification"""

    item_code: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class VendorNameSimilarity(BaseModel):
    """LLM response for vendor name matching"""

    are_similar: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def load_config(config_path: str | None = None) -> dict:
    """Load configuration from file or use defaults.

    Config path is resolved relative to SCRIPT_DIR if not absolute.
    """
    if config_path:
        config_file = Path(config_path)
        # Resolve relative paths relative to script directory
        if not config_file.is_absolute():
            config_file = SCRIPT_DIR / config_file

        if config_file.exists():
            with open(config_file) as f:
                user_config = json.load(f)
                _config_store["CONFIG"] = {**DEFAULT_CONFIG, **user_config}
                print(f"Loaded config from {config_file}")
        else:
            print(f"Warning: Config file not found: {config_file}")
            _config_store["CONFIG"] = DEFAULT_CONFIG.copy()
    else:
        _config_store["CONFIG"] = DEFAULT_CONFIG.copy()

    return _config_store["CONFIG"]


def get_output_folder(case_id: str) -> Path:
    """Get output folder for a case, create if not exists"""
    output_folder = OUTPUT_BASE_DIR / case_id
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder


def extract_pdf_to_markdown(pdf_path: Path) -> str:
    """Extract text from PDF using pdfplumber"""
    markdown_lines = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                markdown_lines.append(f"## Page {page_num}\n")
                text = page.extract_text()
                if text:
                    markdown_lines.append(text)
                    markdown_lines.append("\n---\n")
        return "\n".join(markdown_lines)
    except Exception as e:
        print(f"    Error extracting PDF {pdf_path}: {e}")
        return f"[PDF extraction failed: {e}]"


def extract_pdf_with_gemini(pdf_path: Path) -> str:
    """Extract text from PDF using Gemini multimodal"""
    model = GenerativeModel(
        _gcp_config.GEMINI_FLASH_MODEL,
        generation_config=GenerationConfig(temperature=0),
    )

    with open(pdf_path, "rb") as f:
        pdf_data = f.read()

    pdf_part = Part.from_data(mime_type="application/pdf", data=pdf_data)

    prompt = """Extract ALL text content from this PDF document.
Return the text exactly as it appears, preserving numbers, dates, amounts, and structure.
Do not summarize - extract complete text content."""

    response = model.generate_content([pdf_part, prompt])

    if _gcp_config.API_CALL_DELAY_SECONDS > 0:
        time.sleep(_gcp_config.API_CALL_DELAY_SECONDS)

    return response.text


def extract_pdf_with_fallback(pdf_path: Path) -> tuple[str, str]:
    """Extract PDF with Gemini as default, pdfplumber as fallback"""
    _ensure_gcp_initialized()
    if _gcp_config.PROJECT_ID:
        try:
            content = extract_pdf_with_gemini(pdf_path)
            if content and len(content.strip()) > _MIN_PDF_CONTENT_LENGTH:
                return content, "gemini"
        except Exception as e:
            print(f"    Gemini extraction failed: {e}, using pdfplumber...")

    content = extract_pdf_to_markdown(pdf_path)
    return content, "pdfplumber"


def _strip_markdown_code_block(text: str) -> str:
    """Strip markdown code-block fences from text, returning the inner content."""
    if not text.startswith("```"):
        return text
    lines = text.split("\n")
    json_lines: list[str] = []
    in_block = False
    for line in lines:
        if line.strip().startswith("```"):
            if in_block:
                break
            in_block = True
            continue
        if in_block:
            json_lines.append(line)
    if json_lines:
        return "\n".join(json_lines).strip()
    return text


def _extract_json_object(text: str) -> str:
    """Find and return the first top-level JSON object in *text*."""
    start_idx = text.find("{")
    if start_idx == -1:
        raise ValueError("No JSON object found")

    brace_count = 0
    end_idx = -1
    for i in range(start_idx, len(text)):
        if text[i] == "{":
            brace_count += 1
        elif text[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                end_idx = i + 1
                break

    if end_idx == -1:
        raise ValueError("Unclosed JSON object")

    return text[start_idx:end_idx]


def clean_json_response(response_text: str) -> str:
    """Clean LLM JSON response - remove markdown, fix trailing commas"""
    text = _strip_markdown_code_block(response_text.strip())
    json_str = _extract_json_object(text)
    # Remove trailing commas
    json_str = re.sub(r",(\s*[}\]])", r"\1", json_str)
    return json_str


def normalize_tax_id(tax_id: str) -> str:
    """Remove all non-numeric characters from tax ID"""
    return re.sub(r"[^0-9]", "", tax_id or "")


def validate_abn_checksum(abn: str) -> tuple[bool, str]:
    """Validate Australian Business Number checksum"""
    abn_clean = normalize_tax_id(abn)

    if len(abn_clean) != _ABN_EXPECTED_LENGTH:
        return (
            False,
            f"Invalid length: {len(abn_clean)} (must be {_ABN_EXPECTED_LENGTH})",
        )

    if not abn_clean.isdigit():
        return False, "Contains non-numeric characters"

    weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    checksum = (int(abn_clean[0]) - 1) * weights[0]

    for i in range(1, 11):
        checksum += int(abn_clean[i]) * weights[i]

    if checksum % 89 == 0:
        return True, "Valid checksum"
    return False, f"Invalid checksum (mod 89 = {checksum % 89})"


def validate_tax_id(tax_id: str, format_type: str = "ABN") -> tuple[bool, str]:
    """Validate tax ID based on format type"""
    if format_type == "NONE":
        return True, "Validation disabled"

    if format_type == "ABN":
        return validate_abn_checksum(tax_id)

    # Add other formats as needed (VAT, EIN, etc.)
    return True, "Format validation not implemented"


def call_gemini(
    prompt: str,
    model_name: str | None = None,
    response_schema: type[BaseModel] | None = None,
) -> tuple[Any, float]:
    """Call Gemini API with optional structured output"""
    metrics = _get_metrics()
    model_name = model_name or _gcp_config.GEMINI_FLASH_MODEL
    model = GenerativeModel(
        model_name,
        generation_config=GenerationConfig(temperature=0),
    )

    start_time = time.time()
    response = model.generate_content(prompt)
    latency_ms = (time.time() - start_time) * 1000

    # Update metrics
    usage = response.usage_metadata
    metrics["llm_calls"] += 1
    metrics["total_tokens"]["prompt"] += usage.prompt_token_count
    metrics["total_tokens"]["completion"] += usage.candidates_token_count

    pricing = MODEL_PRICING.get(
        model_name.split("/")[-1], MODEL_PRICING["gemini-3.5-flash"]
    )
    cost = (usage.prompt_token_count / 1_000_000) * pricing["input"]
    cost += (usage.candidates_token_count / 1_000_000) * pricing["output"]
    metrics["total_cost_usd"] += cost

    if _gcp_config.API_CALL_DELAY_SECONDS > 0:
        time.sleep(_gcp_config.API_CALL_DELAY_SECONDS)

    if response_schema:
        json_str = clean_json_response(response.text)
        return response_schema.model_validate_json(json_str), latency_ms

    return response.text, latency_ms


def call_gemini_with_pdf(
    pdf_path: Path,
    prompt: str,
    model_name: str | None = None,
    response_schema: type[BaseModel] | None = None,
) -> tuple[Any, float]:
    """Call Gemini with PDF as input"""
    metrics = _get_metrics()
    model_name = model_name or _gcp_config.GEMINI_PRO_MODEL
    model = GenerativeModel(
        model_name,
        generation_config=GenerationConfig(temperature=0),
    )

    with open(pdf_path, "rb") as f:
        pdf_data = f.read()

    pdf_part = Part.from_data(mime_type="application/pdf", data=pdf_data)

    start_time = time.time()
    response = model.generate_content([pdf_part, prompt])
    latency_ms = (time.time() - start_time) * 1000

    # Update metrics
    usage = response.usage_metadata
    metrics["llm_calls"] += 1
    metrics["total_tokens"]["prompt"] += usage.prompt_token_count
    metrics["total_tokens"]["completion"] += usage.candidates_token_count

    pricing = MODEL_PRICING.get(
        model_name.split("/")[-1], MODEL_PRICING["gemini-3.5-flash"]
    )
    cost = (usage.prompt_token_count / 1_000_000) * pricing["input"]
    cost += (usage.candidates_token_count / 1_000_000) * pricing["output"]
    metrics["total_cost_usd"] += cost

    if _gcp_config.API_CALL_DELAY_SECONDS > 0:
        time.sleep(_gcp_config.API_CALL_DELAY_SECONDS)

    if response_schema:
        json_str = clean_json_response(response.text)
        return response_schema.model_validate_json(json_str), latency_ms

    return response.text, latency_ms


def parse_date(date_str: str | None) -> date | None:
    """Parse date string in various formats"""
    if not date_str:
        return None
    for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y"]:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def check_vendor_name_similarity(name1: str, name2: str) -> tuple[bool, str, float]:
    """Use LLM to check if vendor names are semantically equivalent"""
    prompt = f"""Determine if these two vendor names refer to the SAME business entity.

Name 1: "{name1}"
Name 2: "{name2}"

Consider as SIMILAR:
- Trading names vs legal names
- Abbreviations (Pty Ltd = P/L = PTY LTD)
- Case differences
- Minor punctuation differences

Return ONLY this JSON:
{{"are_similar": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

    try:
        result, _ = call_gemini(
            prompt, _gcp_config.GEMINI_FLASH_MODEL, VendorNameSimilarity
        )
        return result.are_similar, result.reasoning, result.confidence
    except Exception as e:
        return False, f"LLM check failed: {e}", 0.0


# ============================================================================
# BASE AGENT CLASS
# ============================================================================


class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(self, name: str, version: str = "1.0"):
        self.name = name
        self.version = version

    def create_output(self, data: dict, input_refs: list[str] | None = None) -> dict:
        """Wrap agent output with metadata"""
        return {
            "agent": self.name,
            "version": self.version,
            "timestamp": datetime.now().isoformat(),
            "input_refs": input_refs or [],
            **data,
        }

    def save_artifact(self, output_folder: Path, filename: str, data: dict) -> Path:
        """Save artifact to output folder"""
        output_file = output_folder / filename
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  => Saved: {filename}")
        return output_file

    @abstractmethod
    def run(self, *args, **kwargs) -> dict:
        """Execute the agent logic"""


# ============================================================================
# AGENT 1: CLASSIFIER
# ============================================================================


class ClassifierAgent(BaseAgent):
    """Document Classification Agent"""

    def __init__(self):
        super().__init__("classifier")

    def run(self, source_folder: Path, output_folder: Path) -> dict:
        print(" [1/9] Classifier Agent: Starting...")

        files_info = {}
        summary = {"invoice_count": 0, "waf_count": 0}
        invoice_sources = []
        waf_sources = []

        for file_path in source_folder.iterdir():
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() == ".pdf":
                content, method = extract_pdf_with_fallback(file_path)

                # Analyze content
                doc_info = self._analyze_document(content, file_path.name)

                if doc_info.has_invoice:
                    invoice_sources.append(
                        {
                            "path": file_path.name,
                            "full_path": str(file_path),
                            "content": content,
                        }
                    )
                    summary["invoice_count"] += doc_info.invoice_count

                if doc_info.has_work_authorization:
                    waf_sources.append(
                        {
                            "path": file_path.name,
                            "full_path": str(file_path),
                            "content": content,
                        }
                    )
                    summary["waf_count"] += 1

                files_info[file_path.name] = {
                    "type": "pdf",
                    "extraction_method": method,
                    "has_invoice": doc_info.has_invoice,
                    "has_waf": doc_info.has_work_authorization,
                }

            elif file_path.suffix.lower() == ".json":
                files_info[file_path.name] = {"type": "json"}

        files_info["invoice_sources"] = invoice_sources
        files_info["waf_sources"] = waf_sources

        output = self.create_output(
            {
                "source_folder": source_folder.name,
                "files": files_info,
                "summary": summary,
            }
        )

        self.save_artifact(output_folder, "01_classification.json", output)
        print(
            f"   Found {summary['invoice_count']} invoice(s), {summary['waf_count']} WAF(s)"
        )

        return output

    def _analyze_document(self, content: str, filename: str) -> DocumentContent:
        """Analyze document content to identify type"""
        prompt = f"""Analyze this document and identify what types are present.

DOCUMENT CONTENT:
{content[:8000]}

INVOICE INDICATORS:
- Invoice number field
- Line items table with amounts
- Total amounts (subtotal, tax, total)
- Vendor business details and tax ID

WORK AUTHORIZATION INDICATORS:
- Work authorization/WAF header
- Site attendance records
- Authorized hours
- Technician signatures

Return ONLY this JSON:
{{
  "has_invoice": true/false,
  "has_work_authorization": true/false,
  "invoice_count": 0-N,
  "reasoning": "brief explanation"
}}"""

        try:
            result, _ = call_gemini(
                prompt, _gcp_config.GEMINI_FLASH_MODEL, DocumentContent
            )
            return result
        except Exception as e:
            print(f"    Warning: Document analysis failed: {e}")
            # Fallback to keyword detection
            content_lower = content.lower()
            return DocumentContent(
                has_invoice="invoice" in content_lower and "total" in content_lower,
                has_work_authorization="work authorization" in content_lower
                or "waf" in content_lower,
                invoice_count=1 if "invoice" in content_lower else 0,
                reasoning="Keyword fallback",
            )


# ============================================================================
# AGENT 2: EXTRACTOR
# ============================================================================


class ExtractorAgent(BaseAgent):
    """Invoice/WAF Extraction Agent"""

    def __init__(self):
        super().__init__("extractor")

    def run(
        self, source_folder: Path, output_folder: Path, classification: dict
    ) -> dict:
        print(" [2/9] Extractor Agent: Starting...")

        files_info = classification.get("files", {})
        invoice_sources = files_info.get("invoice_sources", [])
        waf_sources = files_info.get("waf_sources", [])

        # Extract invoice
        invoice_data = None
        extraction_failed = False
        extraction_error = None

        if invoice_sources:
            source = invoice_sources[0]
            try:
                invoice_data = self._extract_invoice(Path(source["full_path"]))

                # Validate tax ID if configured
                if _get_config().get("validate_tax_id_checksum") and invoice_data.get(
                    "vendor_tax_id"
                ):
                    tax_valid, tax_reason = validate_tax_id(
                        invoice_data["vendor_tax_id"],
                        _get_config().get("tax_id_format", "ABN"),
                    )
                    invoice_data["_tax_id_validation"] = {
                        "valid": tax_valid,
                        "reason": tax_reason,
                    }

                print(
                    f"   Extracted invoice: {invoice_data.get('invoice_number', 'N/A')}"
                )
            except Exception as e:
                extraction_failed = True
                extraction_error = str(e)
                invoice_data = self._empty_invoice()
        else:
            extraction_failed = True
            extraction_error = "No invoice found"
            invoice_data = self._empty_invoice()

        # Extract WAF if present
        waf_data = None
        if waf_sources:
            try:
                waf_data = self._extract_waf(Path(waf_sources[0]["full_path"]))
                print(f"   Extracted WAF: {waf_data.get('authorized_hours', 0)} hours")
            except Exception as e:
                print(f"   WAF extraction failed: {e}")

        output = self.create_output(
            {
                "invoice": invoice_data,
                "work_authorization": waf_data,
                "extraction_failed": extraction_failed,
                "extraction_error": extraction_error,
                "invoice_count": classification.get("summary", {}).get(
                    "invoice_count", 0
                ),
                "waf_count": classification.get("summary", {}).get("waf_count", 0),
            },
            input_refs=["01_classification.json"],
        )

        self.save_artifact(output_folder, "02_extraction.json", output)
        return output

    def _extract_invoice(self, pdf_path: Path) -> dict:
        """Extract structured invoice data from PDF"""
        prompt = """Extract structured data from this invoice PDF.

Return ONLY valid JSON with these fields:
{
  "invoice_number": "string",
  "invoice_date": "YYYY-MM-DD",
  "invoice_total_inc_tax": decimal,
  "invoice_total_ex_tax": decimal,
  "tax_amount": decimal,
  "vendor_tax_id": "string (tax ID/ABN)",
  "vendor_name": "string",
  "customer_name": "string (who invoice is addressed to)",
  "currency": "AUD/USD/EUR/etc",
  "line_items": [
    {
      "description": "string",
      "quantity": decimal or null,
      "unit_price": decimal or null,
      "amount_ex_tax": decimal,
      "tax_code": "TAX/GST/NA",
      "tax_amount": decimal or null
    }
  ]
}

Extract ALL line items. Use null for missing optional fields."""

        result, _ = call_gemini_with_pdf(
            pdf_path, prompt, _gcp_config.GEMINI_PRO_MODEL, InvoiceExtraction
        )
        return result.model_dump()

    def _extract_waf(self, pdf_path: Path) -> dict:
        """Extract work authorization data from PDF"""
        prompt = """Extract work authorization data from this PDF.

Return ONLY valid JSON:
{
  "reference_number": "string or null",
  "site_name": "string or null",
  "authorized_hours": decimal or null,
  "work_description": "string or null",
  "technician_name": "string or null",
  "date": "YYYY-MM-DD or null"
}"""

        result, _ = call_gemini_with_pdf(
            pdf_path,
            prompt,
            _gcp_config.GEMINI_PRO_MODEL,
            WorkAuthorizationExtraction,
        )
        return result.model_dump()

    def _empty_invoice(self) -> dict:
        """Return empty invoice structure"""
        return {
            "invoice_number": "EXTRACTION_FAILED",
            "invoice_date": "",
            "invoice_total_inc_tax": 0.0,
            "invoice_total_ex_tax": 0.0,
            "tax_amount": 0.0,
            "vendor_tax_id": "",
            "vendor_name": "UNKNOWN",
            "customer_name": None,
            "currency": "AUD",
            "line_items": [],
        }


# ============================================================================
# AGENT 3: PHASE 1 VALIDATOR
# ============================================================================


class Phase1ValidatorAgent(BaseAgent):
    """Phase 1: Initial Intake Validation"""

    def __init__(self):
        super().__init__("phase1_validator")

    def run(self, output_folder: Path, extraction: dict) -> dict:
        print(" [3/9] Phase 1 Validator: Starting...")

        invoice = extraction.get("invoice", {})
        validations = []

        # Step 1.1: Extraction Success
        if extraction.get("extraction_failed"):
            validations.append(
                {
                    "step": "1.1",
                    "rule": "Invoice extraction must succeed",
                    "passed": False,
                    "evidence": extraction.get("extraction_error", "Extraction failed"),
                    "rejection_template": "Document is not a valid Tax Invoice",
                }
            )
        else:
            validations.append(
                {
                    "step": "1.1",
                    "rule": "Invoice extraction must succeed",
                    "passed": True,
                    "evidence": f"Extracted invoice {invoice.get('invoice_number')}",
                }
            )

        # Step 1.2: Customer Verification
        customer_name = (invoice.get("customer_name") or "").lower()
        org_names = [n.lower() for n in _get_config().get("organization_names", [])]
        customer_match = (
            any(org in customer_name for org in org_names) if org_names else True
        )

        validations.append(
            {
                "step": "1.2",
                "rule": "Invoice addressed to organization",
                "passed": customer_match,
                "evidence": f"Customer: {invoice.get('customer_name')}",
                "rejection_template": None
                if customer_match
                else "Invoice addressed to different company",
            }
        )

        # Step 1.3: Tax Compliance
        has_tax_id = bool(invoice.get("vendor_tax_id"))
        has_date = bool(invoice.get("invoice_date"))
        has_vendor = bool(
            invoice.get("vendor_name") and invoice.get("vendor_name") != "UNKNOWN"
        )
        tax_compliant = has_tax_id and has_date and has_vendor

        validations.append(
            {
                "step": "1.3",
                "rule": "Tax compliance (tax ID, date, vendor)",
                "passed": tax_compliant,
                "evidence": f"Tax ID: {has_tax_id}, Date: {has_date}, Vendor: {has_vendor}",
                "rejection_template": None
                if tax_compliant
                else "Document is not a Tax Invoice",
            }
        )

        # Step 1.4: Work Authorization Check
        if _get_config().get("require_work_authorization"):
            work_type = self._determine_work_type(invoice)
            exempt_types = _get_config().get("waf_exempt_work_types", [])
            waf_required = work_type not in exempt_types
            has_waf = extraction.get("waf_count", 0) > 0

            if waf_required:
                validations.append(
                    {
                        "step": "1.4",
                        "rule": "Work authorization required",
                        "passed": has_waf,
                        "evidence": f"WAF required for {work_type}, WAF present: {has_waf}",
                        "rejection_template": None
                        if has_waf
                        else "Missing Work Authorization Form",
                    }
                )

        # Step 1.5: Single Invoice Check
        invoice_count = extraction.get("invoice_count", 1)
        validations.append(
            {
                "step": "1.5",
                "rule": "Single invoice per submission",
                "passed": invoice_count <= 1,
                "evidence": f"Found {invoice_count} invoice(s)",
                "rejection_template": None
                if invoice_count <= 1
                else "Multiple invoices in submission",
            }
        )

        # Determine decision
        failed = [v for v in validations if not v.get("passed")]
        decision = "REJECT" if failed else "CONTINUE"

        output = self.create_output(
            {
                "phase": 1,
                "validations": validations,
                "decision": decision,
                "rejection_template": failed[0].get("rejection_template")
                if failed
                else None,
                "rejection_reason": failed[0].get("evidence") if failed else None,
            },
            input_refs=["02_extraction.json"],
        )

        self.save_artifact(output_folder, "03_phase1_validation.json", output)
        print(f"   Phase 1: {decision}")
        return output

    def _determine_work_type(self, invoice: dict) -> str:
        """Determine work type from invoice content"""
        descriptions = " ".join(
            [
                (line.get("description") or "").lower()
                for line in (invoice.get("line_items") or [])
            ]
        )

        if any(
            kw in descriptions
            for kw in ["preventative", "pm", "scheduled", "maintenance"]
        ):
            return "PREVENTATIVE"
        if any(kw in descriptions for kw in ["cleaning", "clean", "janitorial"]):
            return "CLEANING"
        if any(kw in descriptions for kw in ["emergency", "urgent", "after hours"]):
            return "EMERGENCY"
        return "REPAIRS"


# ============================================================================
# AGENT 4: PHASE 2 VALIDATOR
# ============================================================================


class Phase2ValidatorAgent(BaseAgent):
    """Phase 2: Content Validation"""

    def __init__(self):
        super().__init__("phase2_validator")

    def run(self, output_folder: Path, extraction: dict, phase1: dict) -> dict:
        print(" [4/9] Phase 2 Validator: Starting...")

        invoice = extraction.get("invoice", {})
        validations = []

        # Step 2.1: Line Items Present
        line_count = len(invoice.get("line_items") or [])
        validations.append(
            {
                "step": "2.1",
                "rule": "Invoice has line items",
                "passed": line_count > 0,
                "evidence": f"Found {line_count} line item(s)",
                "rejection_template": None
                if line_count > 0
                else "Invoice charges not itemized",
            }
        )

        # Step 2.2: PO Validation (if required)
        # Note: This would need PO data from preprocessing - simplified here
        if _get_config().get("require_purchase_order"):
            validations.append(
                {
                    "step": "2.2",
                    "rule": "Valid purchase order",
                    "passed": True,  # Would check PO in real implementation
                    "evidence": "PO validation skipped (no preprocessing data)",
                }
            )

        # Determine decision
        failed = [v for v in validations if not v.get("passed")]
        decision = "REJECT" if failed else "CONTINUE"

        output = self.create_output(
            {
                "phase": 2,
                "validations": validations,
                "decision": decision,
                "rejection_template": failed[0].get("rejection_template")
                if failed
                else None,
            },
            input_refs=["02_extraction.json", "03_phase1_validation.json"],
        )

        self.save_artifact(output_folder, "04_phase2_validation.json", output)
        print(f"   Phase 2: {decision}")
        return output


# ============================================================================
# AGENT 5: PHASE 3 VALIDATOR (External)
# ============================================================================


class Phase3ValidatorAgent(BaseAgent):
    """Phase 3: External Validation (duplicates, vendor matching)"""

    def __init__(self):
        super().__init__("phase3_validator")

    def run(self, output_folder: Path, extraction: dict, phase2: dict) -> dict:
        print(" [5/9] Phase 3 Validator: Starting...")

        invoice = extraction.get("invoice", {})
        validations = []

        # Step 3.1: Duplicate Detection
        if _get_config().get("duplicate_check_enabled"):
            # Placeholder - would integrate with actual duplicate check
            validations.append(
                {
                    "step": "3.1",
                    "rule": "Not a duplicate invoice",
                    "passed": True,
                    "evidence": "Duplicate check not implemented",
                }
            )

        # Step 3.2: Tax ID Validation
        tax_validation = invoice.get("_tax_id_validation", {})
        if tax_validation:
            validations.append(
                {
                    "step": "3.2",
                    "rule": "Valid tax ID checksum",
                    "passed": tax_validation.get("valid", True),
                    "evidence": tax_validation.get("reason", "Not validated"),
                    "rejection_template": None
                    if tax_validation.get("valid")
                    else "Vendor tax ID invalid",
                }
            )

        # Step 3.3: Future Date Check
        invoice_date = parse_date(invoice.get("invoice_date"))
        today = date.today()

        if invoice_date:
            is_future = invoice_date > today
            validations.append(
                {
                    "step": "3.3",
                    "rule": "Invoice not future dated",
                    "passed": not is_future,
                    "evidence": f"Invoice date: {invoice.get('invoice_date')}",
                    "rejection_template": None
                    if not is_future
                    else "Invoice is future dated",
                }
            )

        # Determine decision
        failed = [v for v in validations if not v.get("passed")]
        decision = "REJECT" if failed else "CONTINUE"

        output = self.create_output(
            {
                "phase": 3,
                "validations": validations,
                "decision": decision,
                "rejection_template": failed[0].get("rejection_template")
                if failed
                else None,
            },
            input_refs=["02_extraction.json", "04_phase2_validation.json"],
        )

        self.save_artifact(output_folder, "05_phase3_validation.json", output)
        print(f"   Phase 3: {decision}")
        return output


# ============================================================================
# AGENT 6: PHASE 4 VALIDATOR (Calculations)
# ============================================================================


class Phase4ValidatorAgent(BaseAgent):
    """Phase 4: Calculation Validation"""

    def __init__(self):
        super().__init__("phase4_validator")

    def run(self, output_folder: Path, extraction: dict, phase3: dict) -> dict:
        print(" [6/9] Phase 4 Validator: Starting...")

        invoice = extraction.get("invoice", {})
        waf = extraction.get("work_authorization") or {}
        validations = []

        # Step 4.1: Total Verification
        total_inc = invoice.get("invoice_total_inc_tax", 0)
        total_ex = invoice.get("invoice_total_ex_tax", 0)
        tax = invoice.get("tax_amount", 0)

        expected_total = total_ex + tax
        balance = abs(total_inc - expected_total)
        tolerance = _get_config().get("balance_tolerance", 0.02)

        validations.append(
            {
                "step": "4.1",
                "rule": "Total = Subtotal + Tax",
                "passed": balance <= tolerance,
                "evidence": f"Total: {total_inc}, Expected: {expected_total}, Diff: {balance:.2f}",
            }
        )

        # Step 4.2: Line Sum Validation
        line_total = sum(
            (item.get("amount_ex_tax") or 0)
            for item in (invoice.get("line_items") or [])
        )
        line_diff = abs(line_total - total_ex)
        line_tolerance = _get_config().get("line_sum_tolerance", 1.00)

        validations.append(
            {
                "step": "4.2",
                "rule": "Sum of lines = Subtotal",
                "passed": line_diff <= line_tolerance,
                "evidence": f"Line sum: {line_total:.2f}, Subtotal: {total_ex:.2f}, Diff: {line_diff:.2f}",
                "rejection_template": None
                if line_diff <= line_tolerance
                else "Invoice amounts do not reconcile",
            }
        )

        # Step 4.3: WAF Hours Check
        # Determine work type to check WAF exemption
        work_type = self._determine_work_type(invoice)
        exempt_types = [
            t.upper() for t in _get_config().get("waf_exempt_work_types", [])
        ]
        waf_required = work_type not in exempt_types

        invoice_hours = self._calculate_labour_hours(invoice)
        waf_hours = waf.get("authorized_hours", 0) if waf else 0
        hours_tolerance = _get_config().get("hours_tolerance", 0.5)

        if waf and waf_hours and waf_hours > 0:
            # WAF present with authorized hours — check limits
            hours_valid = invoice_hours <= waf_hours + hours_tolerance
            validations.append(
                {
                    "step": "4.3",
                    "rule": "Labour hours within authorization",
                    "passed": hours_valid,
                    "evidence": f"Invoice: {invoice_hours}h, Authorized: {waf_hours}h, Work type: {work_type}",
                    "rejection_template": None
                    if hours_valid
                    else "Invoice does not match work authorization",
                }
            )
        elif waf_required and invoice_hours > 0 and (not waf or not waf_hours):
            # Non-exempt work type has labour hours but no WAF authorization
            validations.append(
                {
                    "step": "4.3",
                    "rule": "Labour hours within authorization",
                    "passed": False,
                    "evidence": (
                        f"Invoice: {invoice_hours}h, Work type: {work_type} (non-exempt), "
                        f"WAF authorized hours: {waf_hours} — no authorization for billed labour"
                    ),
                    "rejection_template": "Invoice does not match work authorization",
                }
            )

        # Determine decision
        failed = [v for v in validations if not v.get("passed")]
        decision = "REJECT" if failed else "ACCEPT"

        output = self.create_output(
            {
                "phase": 4,
                "validations": validations,
                "decision": decision,
                "rejection_template": failed[0].get("rejection_template")
                if failed
                else None,
            },
            input_refs=["02_extraction.json", "05_phase3_validation.json"],
        )

        self.save_artifact(output_folder, "06_phase4_validation.json", output)
        print(f"   Phase 4: {decision}")
        return output

    def _determine_work_type(self, invoice: dict) -> str:
        """Determine work type from invoice line item descriptions."""
        descriptions = " ".join(
            [
                (line.get("description") or "").lower()
                for line in (invoice.get("line_items") or [])
            ]
        )

        if any(
            kw in descriptions
            for kw in ["preventative", "pm", "scheduled", "maintenance"]
        ):
            return "PREVENTATIVE"
        if any(kw in descriptions for kw in ["cleaning", "clean", "janitorial"]):
            return "CLEANING"
        if any(kw in descriptions for kw in ["emergency", "urgent", "after hours"]):
            return "EMERGENCY"
        return "REPAIRS"

    def _calculate_labour_hours(self, invoice: dict) -> float:
        """Calculate total labour hours from invoice"""
        total = 0.0
        labour_keywords = ["labour", "labor", "technician", "hours"]

        for line in invoice.get("line_items") or []:
            desc = (line.get("description") or "").lower()
            if any(kw in desc for kw in labour_keywords):
                qty = line.get("quantity") or 0
                if qty > 0:
                    total += qty
        return total


# ============================================================================
# AGENT 7: TRANSFORMER
# ============================================================================


class TransformerAgent(BaseAgent):
    """Line Item Transformation Agent"""

    VALID_ITEM_CODES: ClassVar[list[str]] = [
        "LABOUR",
        "LABOUR_AH",
        "PARTS",
        "FREIGHT",
        "TRAVEL",
        "CALLOUT",
        "HIRE",
        "CLEANING",
        "OTHER",
    ]

    # Tax code normalization map — extracted values are mapped to
    # the canonical codes expected by downstream systems and eval.
    TAX_CODE_MAP: ClassVar[dict[str, str]] = {
        "GST": "TAX",
        "gst": "TAX",
        "Gst": "TAX",
        "VAT": "TAX",
        "vat": "TAX",
    }

    def __init__(self):
        super().__init__("transformer")

    def run(self, output_folder: Path, extraction: dict, phase4: dict) -> dict:
        print(" [7/9] Transformer Agent: Starting...")

        invoice = extraction.get("invoice", {})
        currency = invoice.get("currency", "AUD")
        tax_rate = _get_config().get("tax_rates_by_currency", {}).get(currency, 0.10)

        line_items = invoice.get("line_items") or []

        # Classify all line items in a single LLM call for efficiency
        descriptions = [line.get("description", "") for line in line_items]
        item_codes = self._classify_items_llm(descriptions)

        mapped_items = []
        for idx, line in enumerate(line_items):
            item_code = item_codes[idx] if idx < len(item_codes) else "OTHER"
            amount = line.get("amount_ex_tax") or 0
            tax = line.get("tax_amount") or (amount * tax_rate)

            # Normalize tax code (e.g. GST -> TAX)
            raw_tax_code = line.get("tax_code", "TAX")
            tax_code = self.TAX_CODE_MAP.get(raw_tax_code, raw_tax_code)

            mapped_items.append(
                {
                    "line_number": idx + 1,
                    "item_code": item_code,
                    "description": line.get("description", ""),
                    "quantity": f"{line.get('quantity') or 1:.2f}",
                    "unit_cost": f"{line.get('unit_price') or amount:,.2f}",
                    "line_cost": f"{amount:,.2f}",
                    "tax": f"{tax:.2f}",
                    "tax_code": tax_code,
                }
            )

        # Calculate totals
        totals = {
            "line_cost_total": sum(
                float(i["line_cost"].replace(",", "")) for i in mapped_items
            ),
            "tax_total": sum(float(i["tax"]) for i in mapped_items),
        }
        totals["grand_total"] = totals["line_cost_total"] + totals["tax_total"]

        output = self.create_output(
            {
                "currency": currency,
                "tax_rate": tax_rate,
                "line_items_mapped": mapped_items,
                "totals": totals,
            },
            input_refs=["02_extraction.json", "06_phase4_validation.json"],
        )

        self.save_artifact(output_folder, "07_transformation.json", output)
        print(f"   Mapped {len(mapped_items)} line items")
        return output

    def _classify_items_llm(self, descriptions: list[str]) -> list[str]:
        """Classify all line item descriptions using a single LLM call.

        Uses Gemini to semantically classify each line item description into
        one of the valid item codes, rather than relying on brittle keyword matching.
        Falls back to 'OTHER' on failure.
        """
        if not descriptions:
            return []

        items_block = "\n".join(
            f'  {i + 1}. "{desc}"' for i, desc in enumerate(descriptions)
        )

        prompt = f"""Classify each invoice line item description into exactly one item code.

VALID ITEM CODES:
- LABOUR: Work performed by technicians, engineers, tradespeople. Includes service calls,
  inspections, diagnostics, calibration, testing, system checks, standard-hours work.
- LABOUR_AH: After-hours or overtime labour only.
- PARTS: Physical materials, components, equipment, replacement parts, filters, coils,
  fittings, valves, units, supplies, consumables — any tangible item purchased/installed.
- FREIGHT: Delivery, shipping, freight charges.
- TRAVEL: Travel time, mileage, kilometre charges, travel allowances.
- CALLOUT: Call-out fees, attendance fees, minimum charges for site visits.
- HIRE: Equipment hire or rental charges.
- CLEANING: Cleaning services, janitorial work.
- OTHER: Only if the description truly does not fit any of the above categories.

LINE ITEMS TO CLASSIFY:
{items_block}

IMPORTANT RULES:
- Physical items (filters, coils, fittings, parts, materials, equipment, units) are PARTS.
- Service work (calibration, diagnostics, testing, inspection, repair labour) is LABOUR.
- Prefer a specific code over OTHER. Only use OTHER as a last resort.

Return ONLY a JSON object in this exact format:
{{"classifications": [{{"item_number": 1, "item_code": "CODE", "reasoning": "brief reason"}}, ...]}}"""

        try:
            result, _ = call_gemini(prompt, _gcp_config.GEMINI_FLASH_MODEL)
            json_str = clean_json_response(result)
            parsed = json.loads(json_str)
            classifications = parsed.get("classifications", [])

            # Build result list, validating each code
            codes = []
            for i, _desc in enumerate(descriptions):
                item_num = i + 1
                match = next(
                    (c for c in classifications if c.get("item_number") == item_num),
                    None,
                )
                if match and match.get("item_code") in self.VALID_ITEM_CODES:
                    codes.append(match["item_code"])
                else:
                    codes.append("OTHER")
            return codes

        except Exception as e:
            print(f"    Warning: LLM item classification failed ({e}), using fallback")
            return self._classify_items_keyword_fallback(descriptions)

    def _classify_items_keyword_fallback(self, descriptions: list[str]) -> list[str]:
        """Keyword-based fallback for item classification when LLM is unavailable."""
        KEYWORD_MAP = {
            "LABOUR_AH": ["after hours", "overtime", "a/h", "after-hours"],
            "LABOUR": [
                "labour",
                "labor",
                "technician",
                "installation",
                "service",
                "calibration",
                "diagnostics",
                "inspection",
                "repair",
            ],
            "PARTS": [
                "parts",
                "material",
                "component",
                "supply",
                "filter",
                "coil",
                "fitting",
                "valve",
                "unit",
                "equipment",
                "replacement",
            ],
            "FREIGHT": ["freight", "delivery", "shipping"],
            "TRAVEL": ["travel", "mileage", "kilometre", "kilometer"],
            "CALLOUT": ["call out", "callout", "attendance"],
            "HIRE": ["hire", "rental"],
            "CLEANING": ["cleaning", "clean"],
        }

        codes = []
        for desc in descriptions:
            desc_lower = desc.lower()
            matched = "OTHER"
            for code, keywords in KEYWORD_MAP.items():
                if any(kw in desc_lower for kw in keywords):
                    matched = code
                    break
            codes.append(matched)
        return codes


# ============================================================================
# AGENT 8: OUTPUT GENERATOR
# ============================================================================


class OutputGeneratorAgent(BaseAgent):
    """Final Output Generation Agent"""

    def __init__(self):
        super().__init__("output_generator")

    def run(
        self,
        output_folder: Path,
        extraction: dict,
        transformer: dict,
        decision: str,
        rejection_template: str | None = None,
        rejection_reason: str | None = None,
        rejection_phase: int | None = None,
    ) -> dict:
        print(" [8/9] Output Generator: Starting...")

        invoice = extraction.get("invoice", {})

        # Map decision to status
        status_map = {
            "ACCEPT": "Pending Payment",
            "REJECT": "Rejected",
            "SET_ASIDE": "To Verify",
            "ERROR": "To Verify",
        }
        invoice_status = status_map.get(decision, "To Verify")

        # Generate outcome message
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if decision == "ACCEPT":
            outcome = f"Invoice accepted for payment on {timestamp}"
        elif decision == "REJECT":
            reason = rejection_template or rejection_reason or "Validation failed"
            outcome = f"Invoice rejected on {timestamp}: {reason}"
        else:
            outcome = f"Invoice requires review as of {timestamp}"

        # Build output
        output_data = {
            "Invoice Processing": {
                "Invoice Type": "Normal",
                "Invoice Status": invoice_status,
                "Invoice Source": "Email",
            },
            "Invoice Details": {
                "Vendor Invoice": invoice.get("invoice_number", ""),
                "Invoice Date": invoice.get("invoice_date", ""),
                "Invoice Total": f"{invoice.get('invoice_total_inc_tax', 0):,.2f}",
                "Pretax Total": f"{invoice.get('invoice_total_ex_tax', 0):,.2f}",
                "Tax Amount": f"{invoice.get('tax_amount', 0):,.2f}",
                "Currency": invoice.get("currency", "AUD"),
            },
            "Vendor Information": {
                "Vendor Name": invoice.get("vendor_name", ""),
                "Tax ID": invoice.get("vendor_tax_id", ""),
            },
            "Line Items": json.dumps(transformer.get("line_items_mapped", [])),
            "Outcome Message": {"Outcome Message": outcome},
        }

        # Save output
        output_file = output_folder / "Postprocessing_Data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"  => Saved: Postprocessing_Data.json (Status: {invoice_status})")

        # Save decision artifact
        decision_output = self.create_output(
            {
                "final_decision": decision,
                "decision_class": decision,  # ACCEPT, REJECT, SET_ASIDE — used by investigation agent
                "invoice_status": invoice_status,
                "rejection_template": rejection_template,
                "rejection_reason": rejection_reason,
                "rejection_phase": f"Phase {rejection_phase}"
                if rejection_phase
                else None,
            }
        )
        self.save_artifact(output_folder, "08_decision.json", decision_output)

        return output_data


# ============================================================================
# AGENT 9: AUDIT LOGGER
# ============================================================================


class AuditLoggerAgent(BaseAgent):
    """Audit Logging Agent"""

    def __init__(self):
        super().__init__("audit_logger")

    def run(
        self,
        output_folder: Path,
        source_folder: Path,
        decision: str,
        processing_time: float,
    ) -> dict:
        print(" [9/9] Audit Logger: Creating audit trail...")

        output = self.create_output(
            {
                "case_id": source_folder.name,
                "source_folder": str(source_folder),
                "output_folder": str(output_folder),
                "processing_summary": {
                    "decision": decision,
                    "processing_time_seconds": round(processing_time, 2),
                    "total_llm_calls": _get_metrics()["llm_calls"],
                    "total_tokens": _get_metrics()["total_tokens"]["prompt"]
                    + _get_metrics()["total_tokens"]["completion"],
                    "total_cost_usd": round(_get_metrics()["total_cost_usd"], 6),
                },
                "artifacts": [
                    "01_classification.json",
                    "02_extraction.json",
                    "03_phase1_validation.json",
                    "04_phase2_validation.json",
                    "05_phase3_validation.json",
                    "06_phase4_validation.json",
                    "07_transformation.json",
                    "08_decision.json",
                    "09_audit_log.json",
                    "Postprocessing_Data.json",
                ],
            }
        )

        self.save_artifact(output_folder, "09_audit_log.json", output)
        return output


# ============================================================================
# ORCHESTRATOR
# ============================================================================


def _handle_phase_rejection(
    output_folder: Path,
    source_folder: Path,
    extraction: dict,
    phase_result: dict,
    phase_num: int,
    start_time: float,
) -> dict:
    """Handle rejection at a specific validation phase."""
    transformer = TransformerAgent()
    transformer_result = transformer.run(output_folder, extraction, phase_result)

    output_gen = OutputGeneratorAgent()
    output_gen.run(
        output_folder,
        extraction,
        transformer_result,
        "REJECT",
        phase_result.get("rejection_template"),
        phase_result.get("rejection_reason"),
        rejection_phase=phase_num,
    )

    audit = AuditLoggerAgent()
    audit.run(output_folder, source_folder, "REJECT", time.time() - start_time)
    return {"decision": "REJECT", "phase": phase_num}


def _run_pipeline(
    source_folder: Path,
    output_folder: Path,
    start_time: float,
) -> dict:
    """Run the main processing pipeline (agents 1-9). Returns result dict."""
    # Agent 1: Classification
    classifier = ClassifierAgent()
    classification = classifier.run(source_folder, output_folder)

    # Agent 2: Extraction
    extractor = ExtractorAgent()
    extraction = extractor.run(source_folder, output_folder, classification)

    # Agent 3: Phase 1 Validation
    phase1 = Phase1ValidatorAgent()
    phase1_result = phase1.run(output_folder, extraction)

    if phase1_result["decision"] == "REJECT":
        return _handle_phase_rejection(
            output_folder,
            source_folder,
            extraction,
            phase1_result,
            1,
            start_time,
        )

    # Agent 4: Phase 2 Validation
    phase2 = Phase2ValidatorAgent()
    phase2_result = phase2.run(output_folder, extraction, phase1_result)

    if phase2_result["decision"] == "REJECT":
        return _handle_phase_rejection(
            output_folder,
            source_folder,
            extraction,
            phase2_result,
            2,
            start_time,
        )

    # Agent 5: Phase 3 Validation
    phase3 = Phase3ValidatorAgent()
    phase3_result = phase3.run(output_folder, extraction, phase2_result)

    if phase3_result["decision"] == "REJECT":
        return _handle_phase_rejection(
            output_folder,
            source_folder,
            extraction,
            phase3_result,
            3,
            start_time,
        )

    # Agent 6: Phase 4 Validation
    phase4 = Phase4ValidatorAgent()
    phase4_result = phase4.run(output_folder, extraction, phase3_result)

    # Agent 7: Transformer
    transformer = TransformerAgent()
    transformer_result = transformer.run(output_folder, extraction, phase4_result)

    # Agent 8: Output Generator
    output_gen = OutputGeneratorAgent()
    output_gen.run(
        output_folder,
        extraction,
        transformer_result,
        phase4_result["decision"],
        phase4_result.get("rejection_template"),
        phase4_result.get("rejection_reason"),
        rejection_phase=4 if phase4_result["decision"] == "REJECT" else None,
    )

    # Agent 9: Audit Logger
    processing_time = time.time() - start_time
    audit = AuditLoggerAgent()
    audit.run(output_folder, source_folder, phase4_result["decision"], processing_time)

    return {
        "decision": phase4_result["decision"],
        "processing_time": processing_time,
        "output_folder": str(output_folder),
    }


def process_invoice(source_folder: Path) -> dict:
    """Main pipeline orchestrator"""
    _ensure_gcp_initialized()
    start_time = time.time()

    case_id = source_folder.name
    output_folder = get_output_folder(case_id)

    print(f"\n{'=' * 60}")
    print(f"Processing: {case_id}")
    print(f"{'=' * 60}")

    # Reset metrics
    _metrics_store["METRICS"] = {
        "llm_calls": 0,
        "total_tokens": {"prompt": 0, "completion": 0},
        "total_cost_usd": 0.0,
        "agent_breakdown": [],
    }

    try:
        return _run_pipeline(source_folder, output_folder, start_time)

    except Exception as e:
        print(f"\n   Error: {e}")
        traceback.print_exc()

        # Save error
        error_file = output_folder / "error.txt"
        error_file.write_text(f"Error: {e}\n\n{traceback.format_exc()}")

        audit = AuditLoggerAgent()
        audit.run(output_folder, source_folder, "ERROR", time.time() - start_time)

        return {"decision": "ERROR", "error": str(e)}


# ============================================================================
# MAIN
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="General Invoice Processing Agent")
    parser.add_argument(
        "--base-dir", "-b", type=str, help="Base directory with case folders"
    )
    parser.add_argument("--case", "-c", type=str, help="Single case folder path")
    parser.add_argument("--config", type=str, help="Path to config JSON file")
    parser.add_argument("--num-cases", "-n", type=int, help="Limit number of cases")

    args = parser.parse_args()

    # Load configuration
    load_config(args.config)

    print("=" * 60)
    print("GENERAL INVOICE PROCESSING AGENT")
    print("=" * 60)
    print(f"Output Dir: {OUTPUT_BASE_DIR}")
    print()

    # Collect cases
    if args.case:
        case_folders = [Path(args.case)]
    elif args.base_dir:
        base_path = Path(args.base_dir)
        if not base_path.exists():
            print(f"Error: Directory not found: {base_path}")
            sys.exit(1)
        case_folders = sorted([d for d in base_path.iterdir() if d.is_dir()])
        if args.num_cases:
            case_folders = case_folders[: args.num_cases]
    else:
        print("Error: Specify --base-dir or --case")
        sys.exit(1)

    print(f"Processing {len(case_folders)} case(s)\n")

    # Process
    stats = {"total": len(case_folders), "accept": 0, "reject": 0, "error": 0}

    for idx, folder in enumerate(case_folders, 1):
        print(f"[{idx}/{len(case_folders)}]", end="")
        result = process_invoice(folder)

        decision = result.get("decision", "ERROR")
        if decision == "ACCEPT":
            stats["accept"] += 1
        elif decision == "REJECT":
            stats["reject"] += 1
        else:
            stats["error"] += 1

        print(f"   Result: {decision}\n")

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total:    {stats['total']}")
    print(f"Accepted: {stats['accept']}")
    print(f"Rejected: {stats['reject']}")
    print(f"Errors:   {stats['error']}")


if __name__ == "__main__":
    main()
