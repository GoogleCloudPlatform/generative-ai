#!/usr/bin/env python3
"""Compare Postprocessing_Data.json files between original and ALF revised versions.
Auto-discovers case folders from the ALF output directory.
"""

import json
import os
from pathlib import Path
from typing import Any

# eval/ lives beside the invoice_processing package; data/ lives inside it
# (see invoice_processing/core/config.py, which is the source of truth).
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "invoice_processing" / "data"
ORIGINAL_BASE = str(DATA_DIR / "agent_output")
ALF_BASE = str(DATA_DIR / "alf_output")


def discover_case_ids() -> list[str]:
    """Discover case IDs from ALF output and original output directories."""
    case_ids = set()
    for base in [ALF_BASE, ORIGINAL_BASE]:
        base_path = Path(base)
        if base_path.exists():
            for entry in base_path.iterdir():
                if entry.is_dir() and (entry / "Postprocessing_Data.json").exists():
                    case_ids.add(entry.name)
    return sorted(case_ids)


def load_json(filepath: str) -> dict[Any, Any]:
    """Load JSON file"""
    try:
        with open(filepath) as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filepath}: {e}")
        return None


def get_nested_value(data: dict, keys: list[str], default=None):
    """Get nested value from dictionary"""
    if data is None:
        return default
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def compare_case(case_id: str) -> dict[str, Any]:
    """Compare Postprocessing_Data.json for a single case"""
    original_path = os.path.join(ORIGINAL_BASE, case_id, "Postprocessing_Data.json")
    alf_path = os.path.join(ALF_BASE, case_id, "Postprocessing_Data.json")

    original_data = load_json(original_path)
    alf_data = load_json(alf_path)

    result = {
        "case_id": case_id,
        "original_exists": original_data is not None,
        "alf_exists": alf_data is not None,
        "identical": False,
        "differences": [],
    }

    # Check if both files exist
    if original_data is None:
        result["differences"].append("Original file does not exist")
        return result

    if alf_data is None:
        result["differences"].append("ALF file does not exist")
        return result

    # Check if files are identical
    if original_data == alf_data:
        result["identical"] = True
        return result

    # Files are different - analyze key differences

    # 1. Invoice Status
    original_status = get_nested_value(
        original_data, ["Invoice Processing", "Invoice Status"]
    )
    alf_status = get_nested_value(alf_data, ["Invoice Processing", "Invoice Status"])

    if original_status != alf_status:
        result["differences"].append(
            {
                "field": "Invoice Processing -> Invoice Status",
                "original": original_status,
                "alf": alf_status,
            }
        )

    # 2. Outcome Message
    original_outcome = get_nested_value(
        original_data, ["Invoice Processing", "Outcome Message"]
    )
    alf_outcome = get_nested_value(alf_data, ["Invoice Processing", "Outcome Message"])

    if original_outcome != alf_outcome:
        result["differences"].append(
            {
                "field": "Invoice Processing -> Outcome Message",
                "original": original_outcome,
                "alf": alf_outcome,
            }
        )

    # 3. Line Items count
    original_line_items = get_nested_value(original_data, ["Line Items"])
    alf_line_items = get_nested_value(alf_data, ["Line Items"])

    original_count = (
        len(original_line_items) if isinstance(original_line_items, list) else 0
    )
    alf_count = len(alf_line_items) if isinstance(alf_line_items, list) else 0

    if original_count != alf_count:
        result["differences"].append(
            {
                "field": "Line Items Count",
                "original": original_count,
                "alf": alf_count,
            }
        )

    # 4. Check for _alf_llm_metadata
    has_alf_metadata = check_for_alf_metadata(alf_data)
    if has_alf_metadata:
        result["differences"].append(
            {
                "field": "_alf_llm_metadata present",
                "value": "YES - LLM was called",
            }
        )

    # 5. Check for other significant differences
    check_other_differences(original_data, alf_data, result)

    return result


def check_for_alf_metadata(data: dict, path: str = "") -> bool:
    """Recursively check for _alf_llm_metadata field"""
    if isinstance(data, dict):
        if "_alf_llm_metadata" in data:
            return True
        for key, value in data.items():
            if check_for_alf_metadata(value, f"{path}.{key}" if path else key):
                return True
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if check_for_alf_metadata(item, f"{path}[{i}]"):
                return True
    return False


def check_other_differences(original: dict, alf: dict, result: dict):
    """Check for other significant differences in top-level keys"""
    original_keys = set(original.keys())
    alf_keys = set(alf.keys())

    # Keys only in original
    only_original = original_keys - alf_keys
    if only_original:
        result["differences"].append(
            {"field": "Keys only in original", "value": list(only_original)}
        )

    # Keys only in ALF
    only_alf = alf_keys - original_keys
    if only_alf:
        result["differences"].append(
            {"field": "Keys only in ALF", "value": list(only_alf)}
        )


def print_comparison_report(results: list[dict]):
    """Print a formatted comparison report"""
    print("=" * 100)
    print("POSTPROCESSING_DATA.JSON COMPARISON REPORT")
    print("=" * 100)
    print()

    identical_count = sum(1 for r in results if r["identical"])
    different_count = sum(
        1
        for r in results
        if not r["identical"] and r["original_exists"] and r["alf_exists"]
    )
    missing_count = sum(
        1 for r in results if not r["original_exists"] or not r["alf_exists"]
    )

    print("Summary:")
    print(f"  - Identical files: {identical_count}")
    print(f"  - Different files: {different_count}")
    print(f"  - Missing files: {missing_count}")
    print()
    print("=" * 100)
    print()

    total = len(results)
    for i, result in enumerate(results, 1):
        print(f"[{i}/{total}] Case ID: {result['case_id']}")
        print("-" * 100)

        if not result["original_exists"]:
            print("  STATUS: Original file does not exist")
        elif not result["alf_exists"]:
            print("  STATUS: ALF file does not exist")
        elif result["identical"]:
            print("  STATUS: NO CHANGES - Files are identical")
        else:
            print("  STATUS: FILES DIFFER")
            print()
            print("  Key Differences:")
            for diff in result["differences"]:
                if isinstance(diff, dict) and "field" in diff:
                    field = diff["field"]
                    if "original" in diff and "alf" in diff:
                        print(f"    - {field}:")
                        print(f"        Original: {diff['original']}")
                        print(f"        ALF:      {diff['alf']}")
                    else:
                        print(f"    - {field}: {diff.get('value', 'N/A')}")
                else:
                    print(f"    - {diff}")

        print()


def main():
    """Main function"""
    case_ids = discover_case_ids()
    if not case_ids:
        print("No cases found in either original or ALF output directories.")
        return

    results = []
    for case_id in case_ids:
        result = compare_case(case_id)
        results.append(result)

    print_comparison_report(results)

    # Also save results to JSON file
    output_file = str(SCRIPT_DIR / "comparison_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
