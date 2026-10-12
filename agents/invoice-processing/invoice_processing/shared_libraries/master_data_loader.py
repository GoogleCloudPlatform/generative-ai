# Master Data Loader -- shared across inference and learning components.
"""Master Data Loader — Shared module for loading and validating master_data.yaml

This module is consumed by eval, investigation agent, ALF, learning agent, and
the admin panel to read domain-specific configuration from a single YAML file.

When no master data file is provided, falls back to invoice-processing defaults
(backward compatible with the existing system).

Usage:
    from master_data_loader import load_master_data

    master = load_master_data("master_data.yaml")
    schema = master.get_extraction_schema("invoice")
    phases = master.get_validation_phases()
    eval_cfg = master.get_eval_schema()
"""

import json
from pathlib import Path
from typing import Any

try:
    import yaml

    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


# ============================================================================
# DEFAULT VALUES (invoice processing — backward compatibility)
# ============================================================================

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_MASTER_DATA_PATH = _SCRIPT_DIR / "invoice_master_data.yaml"


# ============================================================================
# MASTER DATA CLASS
# ============================================================================


class MasterData:
    """Typed accessor for master_data.yaml contents."""

    def __init__(self, data: dict[str, Any], source_path: Path | None = None):
        self._data = data
        self.source_path = source_path
        self.version = data.get("version", "0.0.0")
        self.domain = data.get("domain", "unknown")
        self.display_name = data.get("display_name", "Document Processing")

    # --- Top-level sections ---

    @property
    def raw(self) -> dict[str, Any]:
        """Access the raw parsed dict."""
        return self._data

    # --- Document Types ---

    def get_document_types(self) -> dict[str, Any]:
        return self._data.get("document_types", {})

    def get_primary_document_type(self) -> dict[str, Any]:
        return self.get_document_types().get("primary", {})

    def get_supporting_document_types(self) -> list[dict[str, Any]]:
        supporting = self.get_document_types().get("supporting", [])
        if isinstance(supporting, dict):
            return [supporting]
        return supporting

    # --- Extraction Schemas ---

    def get_extraction_schemas(self) -> dict[str, Any]:
        return self._data.get("extraction_schemas", {})

    def get_extraction_schema(self, doc_type: str) -> dict[str, Any]:
        return self.get_extraction_schemas().get(doc_type, {})

    def get_extraction_fields(self, doc_type: str) -> list[dict[str, Any]]:
        return self.get_extraction_schema(doc_type).get("fields", [])

    def get_line_item_schema(self, doc_type: str) -> dict[str, Any]:
        return self.get_extraction_schema(doc_type).get("line_item_schema", {})

    # --- Taxonomies ---

    def get_taxonomies(self) -> dict[str, Any]:
        return self._data.get("taxonomies", {})

    def get_taxonomy(self, name: str) -> dict[str, Any]:
        return self.get_taxonomies().get(name, {})

    def get_taxonomy_values(self, name: str) -> list[str]:
        return self.get_taxonomy(name).get("values", [])

    def get_tax_code_normalization(self) -> dict[str, str]:
        return self.get_taxonomies().get("tax_code_normalization", {})

    def get_decision_status_mapping(self) -> dict[str, str]:
        return self.get_taxonomies().get("decision_status_mapping", {})

    # --- Validation Pipeline ---

    def get_validation_pipeline(self) -> dict[str, Any]:
        return self._data.get("validation_pipeline", {})

    def get_validation_phases(self) -> list[dict[str, Any]]:
        return self.get_validation_pipeline().get("phases", [])

    def get_phase_config(self, phase_id: str) -> dict[str, Any] | None:
        for phase in self.get_validation_phases():
            if phase.get("id") == phase_id:
                return phase
        return None

    # --- Output Schema ---

    def get_output_schema(self) -> dict[str, Any]:
        return self._data.get("output_schema", {})

    def get_output_sections(self) -> list[dict[str, Any]]:
        return self.get_output_schema().get("sections", [])

    # --- Eval Schema ---

    def get_eval_schema(self) -> dict[str, Any]:
        return self._data.get("eval_schema", {})

    def get_eval_decision_config(self) -> dict[str, Any]:
        return self.get_eval_schema().get("decision", {})

    def get_eval_comparison_groups(self) -> list[dict[str, Any]]:
        return self.get_eval_schema().get("comparison_groups", [])

    def get_eval_comparison_group(self, group_id: str) -> dict[str, Any] | None:
        for group in self.get_eval_comparison_groups():
            if group.get("id") == group_id:
                return group
        return None

    def get_eval_status_to_decision(self) -> dict[str, str]:
        return self.get_eval_decision_config().get("status_to_decision", {})

    def get_eval_decision_path(self) -> str:
        return self.get_eval_decision_config().get("path", "")

    # --- Investigation Config ---

    def get_investigation_config(self) -> dict[str, Any]:
        return self._data.get("investigation", {})

    def get_agent_file_map(self) -> dict[str, str]:
        return self.get_investigation_config().get("agent_file_map", {})

    def get_expected_extraction_fields(self) -> list[str]:
        return self.get_investigation_config().get("expected_extraction_fields", [])

    def get_phase_map(self) -> dict[str, str]:
        """Build phase display name → phase id map from validation pipeline."""
        result = {}
        for phase in self.get_validation_phases():
            phase_id = phase.get("id", "")
            # Create display name like "Phase 1" from "phase1"
            display_name = phase.get("name", phase_id)
            # Also create "Phase N" style keys
            if phase_id.startswith("phase"):
                try:
                    num = phase_id.replace("phase", "")
                    result[f"Phase {num}"] = phase_id
                except ValueError:
                    pass
            result[display_name] = phase_id
        return result

    # --- Config Defaults ---

    def get_config_defaults(self) -> dict[str, Any]:
        return self._data.get("config_defaults", {})

    # --- Labour Detection ---

    def get_labour_detection(self) -> dict[str, Any]:
        return self._data.get("labour_detection", {})

    def get_labour_keywords(self) -> list[str]:
        return self.get_labour_detection().get("keywords", [])

    # --- Artifact Naming ---

    def get_artifacts(self) -> dict[str, str]:
        return self._data.get("artifacts", {})

    # --- Rejection Templates ---

    def get_rejection_templates(self) -> list[dict[str, Any]]:
        return self._data.get("rejection_templates", [])

    # --- Utility ---

    def resolve_dotpath(self, data: dict[str, Any], path: str) -> Any:
        """Resolve a dot-separated path like 'Invoice Processing.Invoice Status'."""
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current


# ============================================================================
# LOADING FUNCTIONS
# ============================================================================


def _find_master_data_file(path: str | None) -> str | None:
    """Search default locations for a master data file.

    Returns the path string if found, or None if no candidate exists.
    """
    candidates = [
        _DEFAULT_MASTER_DATA_PATH,
        _SCRIPT_DIR / "master_data.yaml",
        _SCRIPT_DIR / "master_data.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _resolve_file_path(path: str) -> Path:
    """Resolve and validate the file path, raising if it does not exist."""
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = _SCRIPT_DIR / file_path
    if not file_path.exists():
        raise FileNotFoundError(f"Master data file not found: {file_path}")
    return file_path


def _parse_master_data_file(file_path: Path, text: str) -> dict[str, Any]:
    """Parse file contents as YAML or JSON based on suffix."""
    if file_path.suffix in (".yaml", ".yml"):
        if not _YAML_AVAILABLE:
            raise ImportError(
                "PyYAML is required to load YAML master data files. "
                "Install with: pip install pyyaml"
            )
        return yaml.safe_load(text)
    if file_path.suffix == ".json":
        return json.loads(text)
    # Unknown suffix -- try YAML first, fall back to JSON
    try:
        if _YAML_AVAILABLE:
            return yaml.safe_load(text)
        return json.loads(text)
    except Exception:
        raise ValueError(f"Cannot parse master data file: {file_path}") from None


def load_master_data(path: str | None = None) -> MasterData:
    """Load master data from a YAML or JSON file.

    Args:
        path: Path to master_data.yaml (or .json). If None, looks for
              the default invoice_master_data.yaml in the project root.

    Returns:
        MasterData instance with typed accessors.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the file cannot be parsed.
    """
    if path is None:
        path = _find_master_data_file(path)
        if path is None:
            print("  Warning: No master data file found. Using empty defaults.")
            return MasterData({})

    file_path = _resolve_file_path(path)
    text = file_path.read_text(encoding="utf-8")
    data = _parse_master_data_file(file_path, text)

    if not isinstance(data, dict):
        raise ValueError(
            f"Master data must be a YAML/JSON object, got: {type(data).__name__}"
        )

    master = MasterData(data, source_path=file_path)
    print(
        f"  Loaded master data: {master.display_name} v{master.version} ({file_path.name})"
    )
    return master


def _validate_top_level_fields(master: MasterData) -> list[str]:
    """Check for required top-level fields."""
    warnings: list[str] = []
    if not master.domain:
        warnings.append("Missing 'domain' field")
    if not master.display_name:
        warnings.append("Missing 'display_name' field")
    if not master.get_extraction_schemas():
        warnings.append("No extraction_schemas defined")
    return warnings


def _validate_phases(master: MasterData) -> list[str]:
    """Check validation pipeline phases for completeness."""
    warnings: list[str] = []
    phases = master.get_validation_phases()
    if not phases:
        warnings.append("No validation_pipeline.phases defined")
        return warnings
    for phase in phases:
        if not phase.get("id"):
            warnings.append(f"Phase missing 'id': {phase}")
        if not phase.get("steps"):
            warnings.append(f"Phase '{phase.get('id', '?')}' has no steps")
    return warnings


def _validate_eval_and_investigation(master: MasterData) -> list[str]:
    """Check eval schema and investigation config."""
    warnings: list[str] = []
    if not master.get_eval_schema():
        warnings.append("No eval_schema defined")
    elif not master.get_eval_decision_config():
        warnings.append("eval_schema missing 'decision' config")
    if not master.get_agent_file_map():
        warnings.append("No investigation.agent_file_map defined")
    return warnings


def validate_master_data(master: MasterData) -> list[str]:
    """Validate master data for completeness. Returns list of warnings."""
    warnings: list[str] = []
    warnings.extend(_validate_top_level_fields(master))
    warnings.extend(_validate_phases(master))
    warnings.extend(_validate_eval_and_investigation(master))

    if warnings:
        print(f"  Master data validation: {len(warnings)} warning(s)")
        for w in warnings:
            print(f"    - {w}")

    return warnings
