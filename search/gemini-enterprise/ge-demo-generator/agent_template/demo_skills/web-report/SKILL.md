---
name: web-report
description: Build a polished, self-contained single-page HTML report or briefing microsite - executive briefings, analysis reports, campaign/project one-pagers rendered for the browser. Use whenever the task asks for a web page, HTML report, briefing page, or microsite. Covers page architecture, design system, charts, and delivery.
---

# Web Report Builder

Build a single, self-contained HTML file that presents an analysis or
briefing at the quality of a published product page. Everything inline:
one file, no local assets, no build step.

## Language rule

All user-visible text on the page MUST be written in the same language as
the task description you received. This skill's instructions are English,
but the deliverable follows the task's language. Set the `lang` attribute
on `<html>` accordingly.

## Companion skill

If the `modern-web-guidance` skill is available in your skills directory,
consult it for current best-practice APIs (container queries, View
Transitions, Popover, etc.) while implementing. This skill owns the
STRUCTURE and DESIGN of the report; modern-web-guidance owns modern
platform techniques. Prefer progressive enhancement: the page must remain
fully readable if a modern API is unavailable.

## Hard requirements

- ONE self-contained `.html` file: all CSS in a single `<style>` block,
  all JS in a single `<script>` block, data embedded as one
  `const DATA = {...}` JSON literal.
- Chart library from a CDN is allowed (e.g.
  `https://cdn.jsdelivr.net/npm/chart.js`); everything else inline.
- Responsive from 360px to wide desktop; no horizontal scroll.
- Light and dark theme via CSS custom properties on `:root` and
  `html[data-theme="dark"]`, with a visible toggle. Drive EVERY color
  through the custom properties - hardcoded colors break the other theme.
- Accessible: semantic landmarks (`header`, `main`, `nav`, `footer`),
  one `h1`, ordered heading levels, alt/aria labels on visuals, WCAG AA
  contrast in BOTH themes, visible focus states.
- State on the page that data is a point-in-time snapshot, with the date.

## Page architecture

1. Hero header: report title (assertion, not topic), one-line subtitle,
   date + data-source note, theme toggle.
2. KPI strip: 3-5 stat tiles - big number, short label, delta vs prior
   period with an up/down indicator colored by MEANING (good/bad), not
   by direction.
3. Content sections (3-6), each: section heading as a takeaway sentence,
   short lead paragraph, then a chart / table / card grid. Alternate
   layout patterns between sections so the page has rhythm.
4. Data table section: sortable columns (click header toggles asc/desc),
   free-text filter input, and category filter chips where a dimension
   has few values.
5. Footer: methodology note, sources (real URLs if web research was
   involved), generation date.

## Design system

- Define spacing/type/color as CSS custom properties at the top.
- Palette (light): background `#FFFFFF`, panel `#F2F5FA`, text `#1F2733`,
  muted `#66707F`, primary `#1A2B4A`, accent `#2E6FDB`, warn `#E8A33D`,
  positive `#1E8E5A`, negative `#C6423F`. Derive the dark theme by
  swapping surfaces (`#10151D` background, `#1A212C` panel, `#E8EDF4`
  text), keeping the same accent hues.
- Type scale: 1.25 ratio from a 16px base; page title clamps ~28-40px
  via `clamp()`. System font stack is fine.
- Cards: 12-16px radius, 1px border in a low-contrast border color,
  subtle shadow in light theme only.
- Charts (Chart.js): wrap every canvas in a fixed-height container
  (~320px) with `maintainAspectRatio: false`; colors from the palette
  via `getComputedStyle`; direct axis labels; no more than 5 series on
  one chart; re-render charts on theme toggle so their colors follow.
- Max content width ~1080px, centered; KPI strip and card grids use
  CSS grid with `auto-fit, minmax()`.

## Content quality bar

- Section headings are findings ("Repeat buyers drive 62% of revenue"),
  not labels ("Revenue analysis").
- Every number on the page must come from the provided data or cited
  web research. No invented figures.
- Keep prose tight: lead paragraphs of 2-3 sentences; let visuals carry
  detail.

## Verification (mandatory)

- If Node.js is available, syntax-check the embedded script: extract the
  `<script>` body to a temp `.js` file (strip the DOM calls into a guard
  or use `node --check`).
- `python3 -c "import html.parser"`-based or regex sanity pass: every
  `id` referenced by `getElementById` exists; `DATA` parses as JSON
  (extract and `json.loads` it).
- Open-check with a headless fetch if a browser is unavailable: at
  minimum re-read the file and confirm both theme blocks, the toggle
  handler, and all section headings are present.
Fix and rebuild until clean.

## Delivery

1. Save with a descriptive filename, e.g. `q3_briefing.html`.
2. If the task provided an upload URL for deliverables, upload with:
   `curl -sS -X PUT --upload-file <file> -H "Content-Type: text/html; charset=utf-8" "<upload_url>"`
   Retry once on failure.
3. In your final report, state the filename and list the sections with
   their one-line findings.
