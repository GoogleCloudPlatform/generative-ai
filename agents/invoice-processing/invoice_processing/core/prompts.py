"""LLM Prompt Templates for the Learning Agent.

All prompts used by rule_discoverer.py are defined here.
Prompts encode: available operators, rule schema, conservative domain principles,
and the rules book context needed for rule generation.
"""

# ---------------------------------------------------------------------------
# Rule Discovery System Prompt
# ---------------------------------------------------------------------------

RULE_DISCOVERY_SYSTEM_PROMPT = """\
You are the ALF Learning Agent's Rule Discovery engine.

Your job: Given an invoice processing case where the acting agent produced an \
incorrect result, and given the SME's description of what should change, \
propose a NEW ALF rule (or modification to an existing rule) that would \
correct this case and similar future cases.

=== CRITICAL PRINCIPLE: CONSERVATIVE DOMAIN ===
The rule's conditions MUST be as NARROW as possible to avoid unintended side effects.
- ALWAYS include the phase decision condition (which phase rejected/set-aside)
- ALWAYS include the rejection template condition (narrows to specific failure reason)
- Add domain-specific conditions that capture WHY the agent was wrong
- NEVER create a rule that matches broadly (e.g., all rejections)
- Prefer specific field matches over general patterns

=== AVAILABLE CONDITION OPERATORS ===
equals              - Exact match (case-insensitive for strings)
not_equals           - Value does not match
contains             - String contains substring (case-insensitive). PREFERRED for rejection_template matching.
not_contains         - String does not contain
in_list              - Value is one of a list, e.g. ["REJECT", "SET_ASIDE"]
not_in_list          - Value is not in list
greater_than         - Numeric >
less_than            - Numeric <
greater_equal        - Numeric >=
less_equal           - Numeric <=
regex_match          - Regex pattern match (case-insensitive). Use ONLY when pattern matching is truly needed.
is_true              - Boolean true check (value must be null)
is_false             - Boolean false check (value must be null)
is_null              - None/null check
is_not_null          - Not null
starts_with          - String starts with prefix
any_item_contains    - Checks if ANY item in an array of objects has a string field containing the pattern.
                       Pipe-separated for multiple patterns: "pattern1|pattern2|pattern3"
                       IMPORTANT: The field path must point to the ARRAY itself, NOT to a sub-field.
                       CORRECT:   "field": "extraction.invoice.line_items",  "operator": "any_item_contains", "value": "portapack|oxygen"
                       WRONG:     "field": "invoice.line_items[*].description",  (this path does NOT work)
first_word_equals    - First significant word matches (skips PTY, LTD, THE, etc.)
                       Supports dynamic resolution: value "_DYNAMIC_preprocessing.vendor_name_" resolves at runtime
length_equals        - Length of string/array equals N
length_greater       - Length > N
length_less          - Length < N

=== CRITICAL FIELD PATH RULES ===
- Use ONLY the exact field paths listed below. Do NOT invent paths.
- Do NOT use array indexing syntax like [*], [0], etc. It will NOT resolve.
- For rejection_template matching, use "contains" operator, NOT "equals" or "regex_match".
  The template text may have irregular spacing (e.g. "Vendor  No WAF" with double space).
  "contains" with a substring like "No WAF" is the safest approach.
- For line item matching, use field "extraction.invoice.line_items" with "any_item_contains".

=== AVAILABLE CONTEXT FIELDS (dot-notation paths) ===
Top-level (flattened from agent artifacts):
  decision_phase1     - Phase 1 decision: "CONTINUE" or "REJECT"
  decision_phase2     - Phase 2 decision
  decision_phase3     - Phase 3 decision: "CONTINUE" or "REJECT"
  decision_phase4     - Phase 4 decision: "ACCEPT" or "REJECT"
  work_type           - Detected work type (from Phase 1, if present)
  has_waf             - Boolean: WAF present (waf_count > 0)
  waf_count           - Integer: number of WAFs detected
  waf_exempt          - Boolean: work type is WAF-exempt
  waf_exempt_reason   - String: exemption reason

Phase artifacts (nested):
  phase1.rejection_template  - Phase 1 rejection text (use "contains" operator)
  phase1.validations         - Array of step results
  phase2.rejection_template  - Phase 2 rejection text (use "contains" operator)
  phase3.rejection_template  - Phase 3 rejection text (use "contains" operator)
  phase3.rejection_reason    - Phase 3 rejection reason (use "contains" operator)
  phase4.rejection_template  - Phase 4 rejection text (use "contains" operator)

Invoice data (from extraction):
  invoice.vendor_name            - Vendor name from invoice
  invoice.customer_name          - Customer name from invoice
  invoice.vendor_tax_id          - Vendor tax ID (e.g., ABN)
  invoice.invoice_total_inc_tax  - Total including tax
  invoice.invoice_total_ex_tax   - Total excluding tax
  invoice.tax_amount             - Tax amount
  invoice.currency               - Currency code (AUD, USD, EUR, etc.)
  invoice.invoice_date           - Invoice date (YYYY-MM-DD)
  invoice.line_items             - Array of line item objects (use with any_item_contains)
  invoice._tax_id_validation.valid  - Boolean: tax ID checksum result

Extraction (raw artifact):
  extraction.invoice.vendor_tax_id  - Tax ID from extraction
  extraction.invoice.line_items     - Array of line item objects (use with any_item_contains)
  extraction.waf_count              - Number of WAFs detected
  extraction.extraction_failed      - Boolean: whether extraction failed

=== EXAMPLES OF CORRECT CONDITIONS ===
Example 1 - Customer entity variant rejection:
  {"field": "decision_phase1", "operator": "equals", "value": "REJECT"}
  {"field": "phase1.rejection_template", "operator": "contains", "value": "different company"}
  {"field": "invoice.customer_name", "operator": "regex_match", "value": "(?i)\\bacme\\s*(pty|group|holdings)\\b"}

Example 2 - WAF hours enforcement (agent accepted but should reject):
  {"field": "decision_phase4", "operator": "in_list", "value": ["ACCEPT", "CONTINUE"]}
  {"field": "has_waf", "operator": "is_false", "value": null}
  {"field": "extraction.invoice.line_items", "operator": "any_item_contains", "value": "labour|labor|technician|installation"}

Example 3 - Tax ID validation inconsistency:
  {"field": "decision_phase1", "operator": "equals", "value": "CONTINUE"}
  {"field": "invoice._tax_id_validation.valid", "operator": "is_false", "value": null}

=== AVAILABLE ACTION TYPES ===
llm_continue_processing  - Call LLM to continue full pipeline from a resume point
  Required fields: resume_from (phase2/phase3/phase4/transformer), correction_context
  Use when: agent terminated early (rejected/set-aside) but should have continued
  THIS IS THE PREFERRED ACTION for rejection overrides — it re-runs the pipeline
  from the phase after the incorrect rejection, producing a proper ACCEPT decision
  with all downstream fields filled in correctly.
  Example: {"type": "llm_continue_processing", "resume_from": "phase4",
            "correction_context": "SME Override: explanation of why rejection was wrong"}

llm_patch_fields         - Call LLM to surgically correct specific output fields
  Required fields: target_fields (list of field paths), patch_context
  Use when: agent completed pipeline but got specific fields wrong

set_field                - Deterministically set a field value
  Required fields: target (field path), value
  Use when: simple value override, no LLM needed

override_decision        - Override the final decision
  Required fields: value (ACCEPT/REJECT/SET_ASIDE)
  WARNING: This only changes the decision label without re-running downstream phases.
  For rejection overrides, PREFER llm_continue_processing instead — it produces
  a complete, correct output with all downstream fields properly filled.

=== RULE SCHEMA ===
Return a JSON object with this structure:
{
  "id": "ALF-NNN",
  "name": "Descriptive rule name",
  "description": "What this rule corrects and why",
  "scope": "unique_scope_identifier",
  "priority": 50,
  "enabled": true,
  "tags": ["tag1", "tag2"],
  "conditions": [
    {"field": "...", "operator": "...", "value": ..., "description": "..."}
  ],
  "actions": [
    {"type": "...", ...action-specific fields...}
  ],
  "metadata": {
    "issue_reference": "Learning Agent - SME guided",
    "severity": "HIGH",
    "cases_affected": ["case_id"],
    "rules_book_section": "Section X.Y",
    "root_cause": "Why the acting agent failed",
    "added_by": "Learning Agent (SME-guided)",
    "added_date": "YYYY-MM-DD"
  }
}

Return ONLY valid JSON. No markdown code blocks. No explanation.
Start with { and end with }.
"""


# ---------------------------------------------------------------------------
# Rule Discovery Task Template
# ---------------------------------------------------------------------------

RULE_DISCOVERY_TASK_TEMPLATE = """\
=== SME FEEDBACK ===
{sme_feedback}

=== TARGET CASE: {case_id} ===

AGENT DECISION: {agent_decision}
REJECTION REASON: {rejection_reason}
FAILING PHASE: {failing_phase}

=== CASE DATA ===
{case_summary}

=== PHASE VALIDATION DETAILS ===
{validation_details}

=== INVOICE DATA ===
{invoice_json}

=== EXTRACTION DATA ===
{extraction_json}

=== EXISTING ALF RULES ===
{existing_rules_json}

=== EXISTING SCOPES (mutual exclusion - only 1 rule per scope fires) ===
{existing_scopes}

=== RULES BOOK CONTEXT (relevant sections) ===
{rules_book_context}

=== YOUR TASK ===
1. Understand what the SME wants changed for this case.
2. Identify the root cause: which validation step/phase caused the wrong result.
3. Propose a rule with CONDITIONS that:
   a. MATCH the target case
   b. Are NARROW enough to avoid matching unrelated cases
   c. Use the phase decision + rejection template as the first 2 conditions
   d. Add domain-specific conditions to tighten the scope
4. Choose the appropriate ACTION type based on where the agent went wrong.
5. Assign the next available rule ID: {next_rule_id}
6. Choose a NEW scope name (avoid existing scopes unless intentionally grouping).
7. Set priority between existing rules' priorities to control evaluation order.
8. Fill in all metadata fields.

Return the complete rule JSON.
"""


# ---------------------------------------------------------------------------
# Rule Revision Task Template
# ---------------------------------------------------------------------------

RULE_REVISION_TASK_TEMPLATE = """\
=== SME REVISION REQUEST ===
{revision_feedback}

=== CURRENT PROPOSED RULE ===
{current_rule_json}

=== IMPACT ASSESSMENT RESULT ===
{impact_summary}

=== CASE DATA (target case: {case_id}) ===
{case_summary}

=== INVOICE DATA ===
{invoice_json}

=== EXTRACTION DATA ===
{extraction_json}

=== YOUR TASK ===
The SME wants to revise the proposed rule based on their feedback.
Modify the rule conditions and/or actions according to the SME's request.

Keep the same rule ID ({rule_id}). Update conditions, actions, and metadata as needed.

The revised rule must still match the target case {case_id}.

Return the complete revised rule JSON.
"""


# ---------------------------------------------------------------------------
# Rules Book Context Extractor
# ---------------------------------------------------------------------------


_MAX_PROMPT_CHARS = 8000


def extract_relevant_rules_book_sections(
    rules_book_text: str,
    failing_phase: str,
    failing_step: str = "",
) -> str:
    """Extract sections from the rules book relevant to the failing phase/step.

    Rather than sending the entire 80K rules book to the LLM, extract
    only the sections relevant to where the agent failed.
    """
    lines = rules_book_text.split("\n")
    sections = []
    current_section = []
    in_relevant = False

    # Phase to section header mapping
    phase_headers = {
        "phase1": ["## 4. Phase 1", "Phase 1 Validation"],
        "phase2": ["## 5. Phase 2", "Phase 2 Validation"],
        "phase3": ["## 6. Phase 3", "Phase 3 Validation"],
        "phase4": ["## 7. Phase 4", "Phase 4 Validation"],
    }

    # Also always include pipeline overview and exception handling
    always_include = ["## 1. Pipeline Overview", "## 9. Exception Handling"]

    relevant_headers = phase_headers.get(failing_phase.lower().replace(" ", ""), [])
    relevant_headers.extend(always_include)

    for line in lines:
        # Detect section headers (## level)
        if line.startswith("## "):
            # Save previous section if relevant
            if in_relevant and current_section:
                sections.append("\n".join(current_section))
            current_section = [line]
            in_relevant = any(h in line for h in relevant_headers)
        elif current_section is not None:
            current_section.append(line)

    # Don't forget last section
    if in_relevant and current_section:
        sections.append("\n".join(current_section))

    result = "\n\n---\n\n".join(sections)

    # Truncate if too long (max ~8K chars)
    if len(result) > _MAX_PROMPT_CHARS:
        result = result[:_MAX_PROMPT_CHARS] + "\n\n[...truncated...]"

    return result if result else "(No relevant rules book sections found)"
