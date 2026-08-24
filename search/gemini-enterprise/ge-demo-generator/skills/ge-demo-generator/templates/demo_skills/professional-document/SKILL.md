---
name: professional-document
description: Produce a formal business document as .docx (python-docx) or PDF (reportlab) - reports, proposals, briefings, one-pagers, meeting summaries. Use whenever the task asks for a written document, report file, proposal, or PDF. Covers structure, typography, build and delivery.
---

# Professional Document Builder

Produce a business document that reads and looks like it was prepared by a
professional analyst: clear structure, restrained typography, real numbers.

## Language rule

All user-visible text in the document MUST be written in the same language
as the task description you received. This skill's instructions are English,
but the deliverable follows the task's language.

## Format choice

- `.docx` (python-docx) when the reader may edit: proposals, drafts,
  working reports. Default choice when the task does not specify.
- PDF (reportlab, `platypus` flowables) when the task says PDF or the
  document is final/customer-facing: signed proposals, formal briefings,
  one-pagers.
- Do NOT use weasyprint or LibreOffice conversion (system dependencies are
  not guaranteed). reportlab and python-docx are pure-python and reliable.
- CJK note (PDF only): reportlab's built-in fonts cannot render Japanese,
  Chinese or Korean. For CJK text register a CID font first:
  `from reportlab.pdfbase import pdfmetrics; from reportlab.pdfbase.cidfonts import UnicodeCIDFont; pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))`
  and set that font on every style. python-docx handles CJK natively.

## Process

1. python-docx, reportlab and matplotlib are usually preinstalled by the
   environment warm-up - try the import first; pip install only if missing.
2. Draft the full document content in markdown first (`draft.md`). Get the
   substance right before any formatting code.
3. Convert the draft to the target format with a build script.
4. Verify (below), fix, rebuild.
5. Deliver (below).

## Structure

Standard business report skeleton - adapt, do not skip levels:

1. Title block: document title, subtitle/purpose, date, author line
   (the requesting organization, not you). Documents longer than ~6 pages
   get a cover page plus a table of contents built from the headings.
2. Executive summary: 3-6 sentences a busy executive could read alone -
   the key finding, the number that matters, the recommendation.
3. Body sections (3-6): each opens with a one-sentence takeaway in bold,
   followed by supporting analysis, tables and figures.
4. Recommendations / next steps: numbered, concrete, each with an owner
   or function and a timeframe where possible.
5. Appendix (optional): methodology, data notes, detailed tables.

One-pagers compress the same skeleton to: title block, summary paragraph,
3-4 key points with numbers, recommendation box.

## Typography and layout

- One font family throughout. Body 10.5-11pt, line spacing 1.15-1.3.
- Heading hierarchy: H1 16-18pt bold, H2 13-14pt bold, H3 11pt bold.
  Use color `#1A2B4A` for headings, near-black `#222222` for body.
- Margins: 2.0-2.5 cm all around. Page numbers in the footer from page 2.
- Numbers that carry the argument go in bold; do not bold whole sentences.
- Tables: bold header row with a light fill (`#F2F5FA`), thin borders,
  right-align numeric columns, thousands separators.
- Charts: matplotlib PNGs at 150+ dpi, sized to the text column width,
  numbered captions below (Figure 1: ...). Same palette as the tables.
- Charts with non-Latin labels (Japanese etc.): matplotlib's default font
  has no CJK glyphs (hollow boxes). Register a font first - for Japanese:
  pip install japanize-matplotlib, then import japanize_matplotlib once.
  For other scripts register a Noto Sans font via
  matplotlib.font_manager.fontManager.addfont(). Verify the rendered PNG
  has no hollow-box glyphs before embedding it.
- Never fake letterhead or signatures.

## Content quality bar

- Every claim backed by the provided data or explicitly sourced web
  research (cite source name + URL inline or in the appendix).
- Round numbers for readability; keep raw precision in appendix tables.
- No filler phrases. Cut any sentence that does not inform a decision.

## Verification (mandatory)

- docx: re-open with python-docx; assert heading structure exists and all
  planned sections are present and non-empty.
- PDF: re-open with `pypdf` (usually preinstalled by warm-up); assert
  expected page count (>= 1) and that extracted text contains the section
  headings AND the CJK strings you wrote (garbled fonts extract as empty
  or replacement characters - if a heading is missing, fix the font).
Fix and rebuild until clean. At least one full review-and-rebuild pass is
mandatory: re-read the built document against the task's stated quality
conditions before delivering.

## Delivery

1. Save with a descriptive filename, e.g. `supplier_risk_briefing.pdf`.
2. If the task provided an upload URL for deliverables, upload with:
   `curl -sS -X PUT --upload-file <file> -H "Content-Type: <mime>" "<upload_url>"`
   (docx mime: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`,
   pdf mime: `application/pdf`). Retry once on failure.
3. In your final report, state the filename, page/section count, and
   reproduce the executive summary verbatim.
