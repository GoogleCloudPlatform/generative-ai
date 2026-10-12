# General Invoice Processing Rules Book

**Version:** 1.1.1
**Generated:** 2026-01-23
**Last Updated:** 2026-02-16

---

## How to Use & Update This Document

> **READ THIS FIRST** — This section explains the role of this document, how it relates to other files, and the protocol for making changes. Any agent or developer modifying the invoice processing system must follow these guidelines to keep documentation consistent.

### Role in the System

This document is the **single source of truth** for invoice processing business rules as implemented by `general_invoice_agent.py`. It describes *what* the system does and *why* — validation rules, thresholds, exemptions, decision outcomes, and rejection templates.

It serves two audiences:
1. **Business audience** — Stakeholders and reviewers who need to understand what the system accepts/rejects and why
2. **Developers** — Engineers who need to understand the business rules behind the code

For *how* the system is implemented (agent architecture, code structure, method signatures, data flow), see `README.md`.

### Companion Documents

| Document | Purpose | Update when |
|----------|---------|-------------|
| **This file** (`reconstructed_rules_book.md`) | Business rules, thresholds, decision tables, templates | Business rules change OR agent logic changes |
| **`README.md`** | Technical architecture, code structure, version history | Code structure changes OR agent logic changes |
| **`general_invoice_agent.py`** | Source of truth for actual implementation | N/A — this is the code itself |

**When updating one, always update the other.** Keep version numbers consistent across all three.

### Structural Conventions (for machine and human parsing)

- **Top-level sections:** `## N. Section Title` (e.g., `## 6. Phase 3 Validation Rules`)
- **Sub-sections:** `### N.M Sub-Title` (e.g., `### 0.2 Tax Settings`)
- **Steps:** `### Step N.M: Description` (e.g., `### Step 1.1: Extraction Success`)

| Phase | Section |
|-------|---------|
| Configuration | `## 0. Configuration & Defaults` |
| Pipeline | `## 1. Pipeline Overview` |
| Classification | `## 2. Document Classification Rules` |
| Extraction | `## 3. Data Extraction Rules` |
| Phase 1 | `## 4. Phase 1 Validation Rules` |
| Phase 2 | `## 5. Phase 2 Validation Rules` |
| Phase 3 | `## 6. Phase 3 Validation Rules` |
| Phase 4 | `## 7. Phase 4 Validation Rules` |
| Transformation | `## 8. Line Item Transformation Rules` |
| Decisions | `## 9. Decision Outcomes` |
| Output | `## 10. Output Generation Rules` |
| Templates | `## 11. Rejection Templates` |

### Update Protocol

Follow these steps whenever the agent's business logic changes:

**Step 1 — Version Header:**
- Increment version (semver: major = pipeline restructure, minor = new rules, patch = threshold/keyword tweaks)
- Update `**Last Updated:**` date
- Add a `### Key Changes in vX.Y.Z:` block

**Step 2 — Section Updates:**
- Identify affected sections and update rules, thresholds, keyword lists, decision tables, templates
- For new features, include: **Condition** (trigger), **Behaviour** (what happens), **Rationale** (why), **Version tag** (when added)
- For new decision paths, update **three places**: the relevant phase section, Section 9 (Decision Outcomes), Section 11 (Rejection Templates)

**Step 3 — Cross-Reference:**
- Update `README.md` with corresponding technical changes (pipeline table, decision table, version history, configuration parameters)

**Step 4 — Consistency Checks:**
- [ ] Keyword lists used in multiple rules are identical across all sections
- [ ] Decision outcome table (Section 9) covers all possible agent decisions
- [ ] Rejection template table (Section 11) lists every template string the agent can emit
- [ ] Version number matches across this file, README.md, and general_invoice_agent.py
- [ ] Table of Contents entries match actual section headers

### Content Guidelines

**Include:** Business rules as conditions/outcomes, threshold values with units, keyword lists, decision tables, rejection template strings, configuration defaults, version tags.

**Do NOT include:** Code snippets, method names, line numbers (those go in README.md), implementation details like "uses regex" (describe the *business rule*, not *how it's computed*), speculative/planned changes, domain-specific vendor names (the general agent is domain-independent).

---

## Document Purpose

This document describes the business rules and validation logic for the general-purpose invoice processing agent. All rules are derived from the implemented system behavior. For technical implementation details, see README.md.

### Key Changes in v1.1.1:
- **Schema Accuracy:** Fixed WAF extraction fields to match code (reference_number, not work_order; added date field)
- **Line Item Fields:** Added missing amount_inc_tax field to line item extraction schema
- **Labour Keywords:** Corrected Phase 4 hours calculation keyword list to include "hours"
- **Governance Alignment:** Updated to follow rules_book_governance.md conventions for general agent

### Key Changes in v1.1.0:
- **Full Alignment:** Reconstructed from actual agent code to accurately reflect implemented behavior
- **Removed Phantom Steps:** Removed vendor name verification (Step 3.3), work order status check (Step 3.4), and tax calculation check (Step 4.3) which were documented but not implemented
- **Configuration Detail:** Added full configuration parameter documentation with defaults
- **Keyword Lists:** Added complete keyword lists for work type and item code classification
- **Corrected Templates:** Rejection templates now match exact strings in the agent code

---

## Table of Contents

0. [Configuration & Defaults](#0-configuration--defaults)
1. [Pipeline Overview](#1-pipeline-overview)
2. [Document Classification Rules](#2-document-classification-rules)
3. [Data Extraction Rules](#3-data-extraction-rules)
4. [Phase 1 Validation Rules](#4-phase-1-validation-rules)
5. [Phase 2 Validation Rules](#5-phase-2-validation-rules)
6. [Phase 3 Validation Rules](#6-phase-3-validation-rules)
7. [Phase 4 Validation Rules](#7-phase-4-validation-rules)
8. [Line Item Transformation Rules](#8-line-item-transformation-rules)
9. [Decision Outcomes](#9-decision-outcomes)
10. [Output Generation Rules](#10-output-generation-rules)
11. [Rejection Templates](#11-rejection-templates)

---

## 0. Configuration & Defaults

The general agent is designed to be domain-independent. All validation parameters are configurable via a JSON configuration file. When no config is provided, default values are used.

### 0.1 Organization Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `organization_names` | `["ACME Corp", "ACME Corporation", "ACME Ltd"]` | Valid customer names for invoice verification (Step 1.2). If empty, customer check is skipped. |

### 0.2 Tax Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `default_tax_rate` | `0.10` (10%) | Default tax rate when currency not found in rates table |
| `validate_tax_id_checksum` | `true` | Whether to validate tax ID checksum |
| `tax_id_format` | `"ABN"` | Tax ID format for checksum validation. Options: `"ABN"`, `"NONE"` |

**Tax Rates by Currency:**

| Currency | Tax Rate |
|----------|----------|
| AUD | 10% |
| NZD | 15% |
| USD | 0% |
| EUR | 20% |

### 0.3 Work Authorization Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `require_work_authorization` | `false` | Whether WAF is required |
| `waf_exempt_work_types` | `["PREVENTATIVE", "CLEANING"]` | Work types that skip WAF requirement |
| `waf_exempt_vendors` | `[]` | Vendors exempt from WAF (configured but not actively checked in code) |

### 0.4 Purchase Order Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `require_purchase_order` | `false` | Whether PO number is required |
| `valid_po_prefixes` | `["PO", "WO", "PR"]` | Valid PO number prefixes (placeholder — validation not yet implemented) |

### 0.5 Duplicate Detection Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `duplicate_check_enabled` | `false` | Whether duplicate detection is active |
| `duplicate_check_type` | `"none"` | Integration type: `"none"`, `"file"`, `"database"`, `"api"` |

> **Note:** Duplicate detection is a placeholder. When enabled, it currently always passes. External integration must be implemented.

### 0.6 Tolerance Settings

| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `balance_tolerance` | `0.02` | Dollars | Tolerance for total balance verification (Step 4.1) |
| `line_sum_tolerance` | `1.00` | Dollars | Tolerance for line sum validation (Step 4.2) |
| `hours_tolerance` | `0.5` | Hours | Tolerance for WAF hours check (Step 4.3) |

### 0.7 Configuration Loading

- Configuration loaded from JSON file via `--config` command-line argument
- User configuration is merged with defaults: user values override defaults, unspecified values retain defaults
- Path can be absolute or relative to the script directory

---

## 1. Pipeline Overview

The invoice processing pipeline consists of 9 sequential agents:

```
Agent 1: Classifier       → 01_classification.json
Agent 2: Extractor        → 02_extraction.json
Agent 3: Phase1Validator   → 03_phase1_validation.json
Agent 4: Phase2Validator   → 04_phase2_validation.json
Agent 5: Phase3Validator   → 05_phase3_validation.json
Agent 6: Phase4Validator   → 06_phase4_validation.json
Agent 7: Transformer       → 07_transformation.json
Agent 8: OutputGenerator   → Postprocessing_Data.json + 08_decision.json
Agent 9: AuditLogger       → 09_audit_log.json
```

### 1.1 Pipeline Flow Logic

```
START
  │
  ├─► Agent 1: Classify documents
  ├─► Agent 2: Extract data from PDFs
  │
  ├─► Agent 3: Phase 1 Validation
  │     └─► If REJECT → Jump to Agent 7 → Agent 8 → Agent 9 → END
  │
  ├─► Agent 4: Phase 2 Validation
  │     └─► If REJECT → Jump to Agent 7 → Agent 8 → Agent 9 → END
  │
  ├─► Agent 5: Phase 3 Validation
  │     └─► If REJECT → Jump to Agent 7 → Agent 8 → Agent 9 → END
  │
  ├─► Agent 6: Phase 4 Validation
  │     └─► Decision: ACCEPT or REJECT
  │
  ├─► Agent 7: Transform line items
  ├─► Agent 8: Generate output
  └─► Agent 9: Create audit log → END
```

**Early Exit:** When any phase returns REJECT, the pipeline skips remaining validation phases but still runs transformation, output generation, and audit logging to produce a complete rejection record.

---

## 2. Document Classification Rules

### 2.1 File Type Handling

The classifier agent analyses each file in the source folder to determine its type.

| Detection | Indicators |
|-----------|------------|
| **Invoice** | Invoice number field, line items table, totals, vendor details |
| **Work Authorization** | Site attendance records, technician signatures, hours worked |
| **Email** | Email headers (From, To, Subject, Date) |

### 2.2 Classification Output

For each document, the classifier produces:
- `has_invoice`: Whether the document contains an invoice
- `has_waf`: Whether the document contains a work authorization form
- `invoice_count`: Number of invoices detected
- `waf_count`: Number of work authorizations detected

---

## 3. Data Extraction Rules

### 3.1 Invoice Extraction Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `invoice_number` | String | Yes | Unique invoice identifier |
| `invoice_date` | Date | Yes | Format: YYYY-MM-DD |
| `invoice_total_inc_tax` | Decimal | Yes | Total including tax |
| `invoice_total_ex_tax` | Decimal | Yes | Total excluding tax |
| `tax_amount` | Decimal | Yes | Tax amount |
| `vendor_name` | String | Yes | Vendor business name |
| `vendor_tax_id` | String | Yes | Tax ID (ABN, VAT, EIN, etc.) |
| `customer_name` | String | Optional | Who invoice is addressed to |
| `currency` | String | Yes | ISO currency code |
| `line_items` | Array | Yes | List of line items |

### 3.2 Line Item Extraction Fields

| Field | Type | Required |
|-------|------|----------|
| `description` | String | Yes |
| `quantity` | Decimal | Optional |
| `unit_price` | Decimal | Optional |
| `amount_ex_tax` | Decimal | Optional |
| `tax_code` | String | Optional (default: "TAX") |
| `tax_amount` | Decimal | Optional |
| `amount_inc_tax` | Decimal | Optional |

### 3.3 Work Authorization Extraction Fields

| Field | Type | Description |
|-------|------|-------------|
| `reference_number` | String | Work authorization reference number |
| `site_name` | String | Site name |
| `authorized_hours` | Decimal | Total authorized hours |
| `work_description` | String | Description of work |
| `technician_name` | String | Technician name |
| `date` | String | Date of work authorization |

### 3.4 Tax ID Validation (at Extraction Time)

For regions with checksum-validated tax IDs, validation occurs during extraction.

**Australian ABN (11 digits):**
1. Normalize: remove all non-numeric characters
2. Verify length is exactly 11 digits
3. Subtract 1 from first digit, multiply by weight 10
4. Multiply remaining digits by weights: [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
5. Sum all products
6. Valid if sum is divisible by 89

**Supported Tax ID Formats:**

| Format | Validation |
|--------|------------|
| `ABN` | Full checksum validation (algorithm above) |
| `NONE` | Validation disabled — always passes |

> **Note:** VAT and EIN formats are configured but not yet implemented. They currently return valid by default.

### 3.5 Extraction Failure Handling

If invoice extraction fails:
- `extraction_failed` is set to `true`
- An empty invoice structure is created with `invoice_number = "EXTRACTION_FAILED"`
- Processing continues to Phase 1 where Step 1.1 will reject the invoice

### 3.6 Date Parsing

Invoice dates are parsed using these formats (tried in order):

| Format | Example |
|--------|---------|
| `DD/MM/YYYY` | 28/11/2025 |
| `YYYY-MM-DD` | 2025-11-28 |
| `DD-MM-YYYY` | 28-11-2025 |
| `YYYY/MM/DD` | 2025/11/28 |
| `MM/DD/YYYY` | 11/28/2025 |

If no format matches, date-dependent validations are skipped.

---

## 4. Phase 1 Validation Rules

**Phase Name:** Initial Intake Checks

### Step 1.1: Extraction Success

| Check | Pass | Fail |
|-------|------|------|
| Invoice extraction did not fail | CONTINUE | REJECT |

**Rejection Template:** `"Document is not a valid Tax Invoice"`

### Step 1.2: Customer Verification

**Rule:** Invoice must be addressed to the processing organization.

| Check | Pass | Fail |
|-------|------|------|
| Customer name contains any configured organization name (case-insensitive) | CONTINUE | REJECT |
| Organization names list is empty | CONTINUE (skip check) | — |

**Default organization names:** `"ACME Corp"`, `"ACME Corporation"`, `"ACME Ltd"`

**Rejection Template:** `"Invoice addressed to different company"`

### Step 1.3: Tax Compliance

**Rule:** Invoice must have required tax invoice elements.

| Condition | Required |
|-----------|----------|
| Vendor tax ID is not empty | Yes |
| Invoice date is not empty | Yes |
| Vendor name is not empty and not "UNKNOWN" | Yes |

All three must be present. If any is missing → REJECT.

**Rejection Template:** `"Document is not a Tax Invoice"`

### Step 1.4: Work Authorization Check (Conditional)

**Rule:** If work authorization is required by configuration, a WAF must be present.

This step is **skipped entirely** if `require_work_authorization = false` (the default).

When enabled:
1. Determine work type from invoice line items (see Section 4.2)
2. If work type is in `waf_exempt_work_types` → CONTINUE (exempt)
3. If work type requires WAF, check `waf_count > 0`

| Check | Pass | Fail |
|-------|------|------|
| WAF not required (config) | CONTINUE (skip) | — |
| Work type is exempt | CONTINUE | — |
| WAF present | CONTINUE | REJECT |

**Rejection Template:** `"Missing Work Authorization Form"`

### Step 1.5: Single Invoice Check

| Check | Pass | Fail |
|-------|------|------|
| Invoice count ≤ 1 | CONTINUE | REJECT |

**Rejection Template:** `"Multiple invoices in submission"`

### 4.2 Work Type Classification

**Purpose:** Categorize the type of maintenance work to determine which validation rules apply (e.g., WAF exemption).

**Classification Method:** Keyword matching against concatenated line item descriptions.

**Work Type Categories (checked in priority order):**

| Priority | Work Type | Keywords |
|----------|-----------|----------|
| 1 | PREVENTATIVE | "preventative", "pm", "scheduled", "maintenance" |
| 2 | CLEANING | "cleaning", "clean", "janitorial" |
| 3 | EMERGENCY | "emergency", "urgent", "after hours" |
| 4 (default) | REPAIRS | — (no keywords; default when no match) |

**Impact on Processing:**

| Work Type | WAF Required (when enabled) |
|-----------|-----------------------------|
| PREVENTATIVE | No (exempt) |
| CLEANING | No (exempt) |
| EMERGENCY | Yes |
| REPAIRS | Yes |

---

## 5. Phase 2 Validation Rules

**Phase Name:** Content Validation

### Step 2.1: Line Items Present

| Check | Pass | Fail |
|-------|------|------|
| Number of line items > 0 | CONTINUE | REJECT |

**Rejection Template:** `"Invoice charges not itemized"`

### Step 2.2: PO Validation (Conditional — Placeholder)

This step is **skipped** if `require_purchase_order = false` (the default).

> **Note:** PO validation logic is a placeholder. When enabled, it currently always passes. Implementation requires integration with a PO/ERP data source.

---

## 6. Phase 3 Validation Rules

**Phase Name:** External Validation

### Step 3.1: Duplicate Detection (Conditional — Placeholder)

This step is **skipped** if `duplicate_check_enabled = false` (the default).

> **Note:** Duplicate detection is a placeholder. When enabled, it currently always passes. Implementation requires integration with a duplicate-check system (database, API, or file-based).

**Planned Rejection Template:** `"Invoice already processed"`

### Step 3.2: Tax ID Checksum Validation

**Rule:** Verify that the extracted tax ID has a valid checksum.

This step is **skipped** if `validate_tax_id_checksum = false` or `tax_id_format = "NONE"`.

| Check | Pass | Fail |
|-------|------|------|
| Tax ID checksum is valid | CONTINUE | REJECT |
| Tax ID format is NONE | CONTINUE (skip) | — |
| Checksum validation disabled | CONTINUE (skip) | — |

**Rejection Template:** `"Vendor tax ID invalid"`

> **Note:** This step validates the tax ID checksum only. It does **not** match the tax ID against vendor master data — that would require external integration.

### Step 3.3: Future Date Check

| Check | Pass | Fail |
|-------|------|------|
| Invoice date ≤ today | CONTINUE | REJECT |
| Invoice date cannot be parsed | CONTINUE (skip) | — |

**Rejection Template:** `"Invoice is future dated"`

---

## 7. Phase 4 Validation Rules

**Phase Name:** Calculation Validation

### Step 4.1: Total Verification (Informational)

**Rule:** Invoice total should equal subtotal plus tax.

```
Expected: invoice_total_inc_tax = invoice_total_ex_tax + tax_amount
Tolerance: $0.02 (configurable via balance_tolerance)
```

| Check | Pass | Fail |
|-------|------|------|
| Difference within tolerance | CONTINUE | CONTINUE |

> **Note:** This step is informational only — it never causes rejection. The result is recorded for audit purposes.

### Step 4.2: Line Sum Validation

**Rule:** Sum of line item amounts should equal the invoice subtotal.

```
Expected: sum(line_items.amount_ex_tax) = invoice_total_ex_tax
Tolerance: $1.00 (configurable via line_sum_tolerance)
```

| Check | Pass | Fail |
|-------|------|------|
| Sum within tolerance | CONTINUE | REJECT |

**Rejection Template:** `"Invoice amounts do not reconcile"`

### Step 4.3: WAF Hours Check (Conditional)

**Rule:** If work authorization data is present with authorized hours, invoice labour hours must not exceed authorized hours.

This step is **skipped** if no WAF data exists or WAF has no `authorized_hours` value.

```
Labour Hours = sum of quantity from line items with labour keywords
Tolerance: 0.5 hours (configurable via hours_tolerance)

Pass if: Labour Hours ≤ Authorized Hours + Tolerance
```

**Labour keywords for hours calculation:** "labour", "labor", "technician", "hours"

| Check | Pass | Fail |
|-------|------|------|
| No WAF data | CONTINUE (skip) | — |
| Hours within tolerance | CONTINUE | REJECT |

**Rejection Template:** `"Invoice does not match work authorization"`

### Phase 4 Decision Logic

Phase 4 uses **binary** decision logic:

```
If any step fails → REJECT
If all steps pass → ACCEPT
```

Phase 4 is the only phase that can return ACCEPT.

---

## 8. Line Item Transformation Rules

### 8.1 Item Code Classification

Line items are classified to standard codes using keyword matching. The first matching code wins.

**Item Codes (checked in priority order):**

| Priority | Item Code | Keywords |
|----------|-----------|----------|
| 1 | `LABOUR` | "labour", "labor", "technician", "installation" |
| 2 | `LABOUR_AH` | "after hours", "overtime", "a/h" |
| 3 | `PARTS` | "parts", "material", "component", "supply" |
| 4 | `FREIGHT` | "freight", "delivery", "shipping" |
| 5 | `TRAVEL` | "travel", "mileage", "kilometre" |
| 6 | `CALLOUT` | "call out", "callout", "attendance" |
| 7 | `HIRE` | "hire", "rental" |
| 8 | `CLEANING` | "cleaning", "clean" |
| 9 (default) | `OTHER` | — (catch-all when no keywords match) |

> **Note:** Priority order matters. A line with "after hours labour" would match `LABOUR` (priority 1) before `LABOUR_AH` (priority 2), because `LABOUR` keywords include "labour". This is a known ordering consideration.

### 8.2 Tax Rate by Currency

| Currency | Tax Rate |
|----------|----------|
| AUD | 10% |
| NZD | 15% |
| USD | 0% |
| EUR | 20% |

Additional currencies use the `default_tax_rate` (default: 10%).

---

## 9. Decision Outcomes

| Decision | Meaning | When Applied |
|----------|---------|--------------|
| `ACCEPT` | Invoice passes all validations, ready for payment | Phase 4 completes with no failures |
| `REJECT` | Invoice fails validation | Any validation step fails |
| `ERROR` | Processing error occurred | Exception during processing |

> **Note:** `SET_ASIDE` is defined in the status mapping but is not currently produced by any validation step. It exists as a configuration option for future implementation (e.g., when duplicate detection or vendor matching is implemented).

---

## 10. Output Generation Rules

### 10.1 Invoice Status Mapping

| Decision | Invoice Status |
|----------|----------------|
| `ACCEPT` | "Pending Payment" |
| `REJECT` | "Rejected" |
| `SET_ASIDE` | "To Verify" |
| `ERROR` | "To Verify" |

### 10.2 Outcome Message Format

| Decision | Message Format |
|----------|----------------|
| ACCEPT | "Invoice accepted for payment on {DD/MM/YYYY HH:MM:SS}" |
| REJECT | "Invoice rejected on {DD/MM/YYYY HH:MM:SS}: {rejection_reason}" |
| Other | "Invoice requires review as of {DD/MM/YYYY HH:MM:SS}" |

### 10.3 Output Structure (Postprocessing_Data.json)

```json
{
  "Invoice Processing": {
    "Invoice Type": "Normal",
    "Invoice Status": "Pending Payment",
    "Invoice Source": "Email"
  },
  "Invoice Details": {
    "Vendor Invoice": "INV-12345",
    "Invoice Date": "15/01/2026",
    "Invoice Total": "1,100.00",
    "Pretax Total": "1,000.00",
    "Tax Amount": "100.00",
    "Currency": "AUD"
  },
  "Vendor Information": {
    "Vendor Name": "ABC Services Pty Ltd",
    "Tax ID": "12345678901"
  },
  "Line Items": "[{...}]",
  "Outcome Message": {
    "Outcome Message": "Invoice accepted for payment on 23/01/2026 14:30:00"
  }
}
```

**Fixed values:**
- Invoice Type: Always `"Normal"` (no other types implemented)
- Invoice Source: Always `"Email"`

### 10.4 Line Item Output Format

```json
{
  "line_number": 1,
  "item_code": "LABOUR",
  "description": "Technician labour - normal hours",
  "quantity": "2.00",
  "unit_cost": "85.00",
  "line_cost": "170.00",
  "tax": "17.00",
  "tax_code": "TAX"
}
```

---

## 11. Rejection Templates

All rejection templates are listed here, grouped by phase.

### Phase 1 Templates

| Template | Trigger |
|----------|---------|
| `"Document is not a valid Tax Invoice"` | Extraction failed (Step 1.1) OR missing tax ID/date/vendor (Step 1.3) |
| `"Invoice addressed to different company"` | Customer name does not match organization (Step 1.2) |
| `"Missing Work Authorization Form"` | WAF required but not present (Step 1.4) |
| `"Multiple invoices in submission"` | More than one invoice detected (Step 1.5) |

### Phase 2 Templates

| Template | Trigger |
|----------|---------|
| `"Invoice charges not itemized"` | No line items found (Step 2.1) |

### Phase 3 Templates

| Template | Trigger |
|----------|---------|
| `"Invoice already processed"` | Duplicate detected (Step 3.1 — placeholder, not yet active) |
| `"Vendor tax ID invalid"` | Tax ID checksum failed (Step 3.2) |
| `"Invoice is future dated"` | Invoice date in the future (Step 3.3) |

### Phase 4 Templates

| Template | Trigger |
|----------|---------|
| `"Invoice amounts do not reconcile"` | Line item sum does not match invoice subtotal (Step 4.2) |
| `"Invoice does not match work authorization"` | Labour hours exceed authorized hours (Step 4.3) |

---

## Appendix A: Artifacts Generated

| Filename | Description |
|----------|-------------|
| `01_classification.json` | Document type classification results |
| `02_extraction.json` | Extracted invoice and WAF data |
| `03_phase1_validation.json` | Phase 1 validation results |
| `04_phase2_validation.json` | Phase 2 validation results |
| `05_phase3_validation.json` | Phase 3 validation results |
| `06_phase4_validation.json` | Phase 4 validation results |
| `07_transformation.json` | Transformed line items with item codes |
| `08_decision.json` | Final decision summary |
| `09_audit_log.json` | Processing metrics and audit trail |
| `Postprocessing_Data.json` | Final output for downstream systems |
| `error.txt` | Error details (if error occurred) |

---

*End of Reconstructed Rules Book*
