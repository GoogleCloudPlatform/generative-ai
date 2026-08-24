---
name: professional-presentation
description: Build a professional, executive-quality presentation deck (.pptx) with python-pptx. Use whenever the task asks for slides, a deck, a board/executive presentation, or a pitch. Covers design system, slide patterns, build process, and delivery.
---

# Professional Presentation Builder

Build a polished 16:9 widescreen deck that looks like it came from a top-tier
consulting firm, using python-pptx. Follow this process end to end.

## Language rule

All user-visible text on the slides (titles, body, labels, notes) MUST be
written in the same language as the task description you received. This
skill's instructions are English, but the deliverable follows the task's
language.

## Process

1. python-pptx and matplotlib are usually preinstalled by the environment
   warm-up - try the import first; `pip install python-pptx` only if missing.
2. Plan the storyline BEFORE writing code. A board-grade deck is:
   title -> agenda -> EXECUTIVE SUMMARY (the conclusion and top 3 findings
   stated up front, one slide) -> 3-5 content sections, each opened by a
   minimal section-divider slide (section number + assertion title on a
   Primary-dark background) -> recommendations/next steps.
   One message per slide. Write the full outline to `outline.md` first.
3. Build the deck with a single Python script (see `scripts/build_deck.py`
   for a working scaffold you should copy and adapt).
4. Render, open-check (see Verification), fix, repeat.
5. Deliver (see Delivery).

Add speaker notes (`slide.notes_slide.notes_text_frame.text`) to the
executive summary and each section's key slide: 2-3 sentences of what to
SAY, not a repeat of the slide text.

## Design system

Apply these rules in code; never rely on template defaults.

- Slide size: 16:9 (13.333 x 7.5 inches). Set explicitly:
  `prs.slide_width = Inches(13.333)`, `prs.slide_height = Inches(7.5)`.
- Color palette (define once as constants):
  - Primary dark `#1A2B4A` (titles, header bars)
  - Accent `#2E6FDB` (highlights, chart series, key numbers)
  - Secondary accent `#E8A33D` (callouts, deltas - use sparingly)
  - Body text `#333F50`, muted `#8A93A6`, background `#FFFFFF`,
    light panel `#F2F5FA`
- Typography: one sans-serif family throughout (Arial is always available).
  Title 30-34pt bold, section header 24-28pt, body 14-18pt, captions 11-12pt.
  Never go below 11pt. Max ~5 bullets per slide, max ~12 words per bullet.
- Layout grid: 0.6in outer margins. Title zone is the top 1.2in. Content
  sits on an invisible 12-column grid; prefer two-column layouts
  (text + visual) over full-width walls of text.
- Every content slide gets a thin accent rule (a 0.03in high rectangle in
  Primary dark) under the title.
- Big-number slides: one KPI per panel, number at 40-54pt in Accent,
  label at 12pt muted, arranged in 2-4 equal panels.
- Charts: prefer generating chart images with matplotlib (same palette,
  no gridline clutter, direct labels instead of legends where possible,
  150+ dpi PNG) and placing them with `add_picture`. Native pptx charts
  are acceptable for simple bar/line.
- Charts with non-Latin text (Japanese, Chinese, Korean, ...): matplotlib's
  default font has NO CJK glyphs - labels render as hollow boxes. BEFORE
  rendering any chart whose labels are not pure ASCII, register a matching
  font. For Japanese the fastest reliable path is:
      pip install japanize-matplotlib
      import japanize_matplotlib   # once, right after importing matplotlib
  For other scripts, download a Noto Sans font that covers the language,
  register it with matplotlib.font_manager.fontManager.addfont(path), and
  set rcParams["font.family"] to it. AFTER rendering, re-open the PNG and
  verify no glyph appears as a hollow box before placing it on a slide.
- Tables: header row filled Primary dark with white bold text, body rows
  alternating white / light panel, 11-12pt.
- Footer on every slide except the title: short deck title left, slide
  number right, 10pt muted.

## Content quality bar

- Slide titles are ASSERTIONS, not topics ("Revenue grew 18% on repeat
  customers", not "Revenue"). A reader should get the argument from
  titles alone.
- Use real numbers from the provided data. Round for readability
  (12.4M, 18%, 3.2x). Never invent figures.
- End with a "Next steps" or "Recommendations" slide containing concrete,
  owner-assignable actions.

## Verification (mandatory)

After building, re-open the file with python-pptx and assert:
- expected slide count;
- no text frame overflows its shape (compare text length vs shape size
  heuristically) and no shape extends beyond slide bounds;
- every slide has a non-empty title, and content slides have the footer
  with the correct slide number;
- iterate every run in every text frame and confirm no character rendered
  from a missing font path (for CJK decks: the deck font must cover the
  script; re-check chart PNGs for hollow-box glyphs).
Fix any issue and rebuild. At least one full review-and-rebuild pass is
mandatory even when the first build looks fine: re-read the deck against
the task's stated quality conditions before delivering.

## Delivery

1. Save as a descriptive filename, e.g. `q3_revenue_review.pptx`.
2. If the task provided an upload URL for deliverables, upload with:
   `curl -sS -X PUT --upload-file <file> -H "Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation" "<upload_url>"`
   Retry once on failure.
3. In your final report, state the filename, slide count, and a one-line
   summary of each slide.
