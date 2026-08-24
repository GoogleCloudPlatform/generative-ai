#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Deployed as a runtime template into the user's Cloud Shell (not imported by
# repo tooling); validated by py_compile and end-to-end demo deployments.
# Repo-level strict lint/typing is intentionally skipped for this generated-
# origin runtime code; incremental typing is planned as follow-up.
# flake8: noqa
# pylint: skip-file
# mypy: ignore-errors
# ruff: noqa


"""Builds the agent's DATA ASSET CATALOG from the CSVs that are about to be loaded.

The generated agent's system instruction asserts that it already knows every
table, every column and the period the data covers, and several rules ("the
catalog above IS your schema", PATH 0, the no-rediscovery MUSTs) are only true
because of that. This script is what makes them true: it reads `data/*.csv`
plus the matching `data/<table>_schema.json` and writes
`adk_agent/app/data_assets.md`, which `agent.py` substitutes into the
`[DATA_ASSET_CATALOG]` placeholder at import time.

Deriving it from the CSVs rather than from BigQuery is deliberate. It runs
before the container build with no cloud round trip, no IAM dependency and no
ordering constraint against the parallel `bq load` job, and the CSVs are the
same rows BigQuery ends up with.

The date coverage is the reason this exists at all. Without it the model opens a
figure question with a MIN/MAX probe to find out what period the synthetic data
covers - a whole round trip the user waits through, on every fresh conversation.

usage: build_data_catalog.py [--data-dir ./data] [--out adk_agent/app/data_assets.md]
"""

import argparse
import csv
import json
import os
import re
import sys

# Anything a human would read as a point in time. The type list is what BigQuery
# reports; the regexes are the fallback for an autodetected column whose schema
# JSON was never written.
_DATE_TYPES = ("DATE", "DATETIME", "TIMESTAMP")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?")

# A categorical column is far more useful to the model as its actual value list
# than as "STRING": it stops the agent guessing `WHERE status = 'Completed'`
# when the data says 'COMPLETE'. Only worth doing while the set stays small.
_MAX_ENUM_VALUES = 8
_MAX_ENUM_LEN = 40
# Descriptions are authored per column and can run long; the catalog is a prompt
# section, not documentation.
_MAX_DESC = 180


def _read_csv(path):
    """Returns (header, rows). Tolerates a BOM and ragged trailing columns."""
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            return [], []
        return [h.strip() for h in header], [r for r in reader if any(c.strip() for c in r)]


def _load_schema(data_dir, table):
    """Column name -> {'type', 'description'} from the BigQuery schema JSON."""
    path = os.path.join(data_dir, table + "_schema.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            fields = json.load(fh)
    except Exception:  # noqa: BLE001 - a malformed schema must not fail the deploy
        return {}
    if not isinstance(fields, list):
        return {}
    out = {}
    for field in fields:
        if isinstance(field, dict) and field.get("name"):
            out[str(field["name"]).strip()] = {
                "type": str(field.get("type", "") or "").upper(),
                "description": str(field.get("description", "") or "").strip(),
            }
    return out


def _table_description(data_dir, table):
    """Optional one-liner describing the grain, written next to the CSV."""
    path = os.path.join(data_dir, table + "_description.txt")
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return " ".join(fh.read().split())
    except Exception:  # noqa: BLE001
        return ""


def _infer_type(values):
    """Best-effort type for a column with no schema JSON entry."""
    seen = [v for v in values if v != ""]
    if not seen:
        return "STRING"
    if all(_DATE_RE.match(v) for v in seen):
        return "TIMESTAMP" if any(len(v) > 10 for v in seen) else "DATE"
    try:
        for v in seen:
            float(v)
    except ValueError:
        return "STRING"
    return "INTEGER" if all(re.match(r"^-?\d+$", v) for v in seen) else "FLOAT"


def _clip(text, limit):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def facts_line(row_count, coverage):
    """The one line of measured fact: how many rows, and what period they cover.

    Shared verbatim between the prompt catalog and the BigQuery table
    description, so Knowledge Catalog shows exactly what the agent was told.
    """
    return "Rows: %d. Coverage: %s" % (
        row_count, "; ".join(coverage) if coverage else "no date column")


def build_table_section(table, header, rows, schema, description):
    """Markdown for one table: grain, row count, date coverage, column list.

    Returns (markdown, facts_line).
    """
    lines = []
    title = "### `%s` - %s" % (table, description) if description else "### `%s`" % table
    lines.append(_clip(title, 400))

    columns, coverage = [], []
    for idx, name in enumerate(header):
        values = [(row[idx].strip() if idx < len(row) else "") for row in rows]
        meta = schema.get(name, {})
        ctype = meta.get("type") or _infer_type(values)
        desc = meta.get("description", "")

        # Clipped BEFORE the value list is appended, never after: a long authored
        # description would otherwise eat the budget and leave the enum severed
        # mid-value ("Sprouts Farmers Marke..."), which is worse than no enum -
        # the model writes the truncated string into a WHERE clause.
        desc = _clip(desc, _MAX_DESC) if desc else ""

        present = [v for v in values if v]
        if ctype in _DATE_TYPES and present:
            lo, hi = min(present), max(present)
            coverage.append("`%s` %s -> %s" % (name, lo[:10], hi[:10]))
            if not desc:
                desc = "date column"
        elif ctype == "STRING" and present:
            distinct = sorted(set(present))
            if (len(distinct) <= _MAX_ENUM_VALUES
                    and max(len(v) for v in distinct) <= _MAX_ENUM_LEN
                    and len(distinct) < len(present)):
                values_txt = "values: " + ", ".join(distinct)
                desc = (desc + " | " + values_txt) if desc else values_txt

        columns.append("`%s` %s%s" % (name, ctype, (" - " + desc) if desc else ""))

    facts = facts_line(len(rows), coverage)
    lines.append(facts)
    lines.extend("  - " + c for c in columns)
    return "\n".join(lines), facts


def build_catalog(data_dir):
    """Walks data_dir once. Returns (catalog_markdown, {table: bq_description}).

    The BigQuery description is the authored grain sentence plus the same facts
    line the prompt gets. Writing it to BigQuery is what puts the row count and
    the coverage window into Knowledge Catalog and the Cloud Console, so the
    catalog a human browses says the same thing as the catalog the agent reads.
    """
    if not os.path.isdir(data_dir):
        return "", {}
    names = sorted(
        f for f in os.listdir(data_dir)
        if f.endswith(".csv") and not f.endswith(".hero.csv")
    )
    sections, descriptions = [], {}
    for name in names:
        table = name[:-4]
        header, rows = _read_csv(os.path.join(data_dir, name))
        if not header:
            continue
        authored = _table_description(data_dir, table)
        section, facts = build_table_section(
            table, header, rows, _load_schema(data_dir, table), authored)
        sections.append(section)
        descriptions[table] = (authored + " " + facts) if authored else facts
    return "\n\n".join(sections), descriptions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="./data")
    parser.add_argument("--out", default="adk_agent/app/data_assets.md")
    args = parser.parse_args()

    catalog, descriptions = build_catalog(args.data_dir)
    if not catalog:
        print("  [CATALOG] No CSVs under %s; nothing to describe." % args.data_dir)
        return 0

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(catalog + "\n")
    print("  [CATALOG] Wrote %s (%d tables, %d chars)."
          % (args.out, catalog.count("\n### ") + 1, len(catalog)))

    # One file per table for the loader to hand to `bq update --description`.
    # A file rather than stdout because the loads run in parallel subshells and
    # the descriptions are free text in the demo's own language - no quoting,
    # no field splitting, no encoding round trip.
    for table, text in sorted(descriptions.items()):
        with open(os.path.join(args.data_dir, table + "_bqdescription.txt"),
                  "w", encoding="utf-8") as fh:
            fh.write(text)
    print("  [CATALOG] Wrote %d BigQuery table description(s) for Knowledge Catalog."
          % len(descriptions))
    return 0


if __name__ == "__main__":
    sys.exit(main())
