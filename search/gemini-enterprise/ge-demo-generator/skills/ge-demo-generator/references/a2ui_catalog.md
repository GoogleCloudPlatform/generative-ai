# A2UI (Agent-to-User Interface) v0.9 & Composite Catalog Reference

The A2UI v0.9 protocol enables AI agents in Gemini Enterprise to declaratively stream rich, interactive user interface components (Cards, Material Tables, Vega Charts, Sandboxed Dashboards, Action Buttons, Suggestion Chips, Side-panel Canvases) directly into the chat interface.

---

## 1. Protocol Overview & Wire Envelopes

Gemini Enterprise speaks **A2UI v0.9** backed by the **Gemini Enterprise composite catalog** (`https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json`) consisting of 52 rich components.

All A2UI payloads must be enclosed within `<a2ui-json> ... </a2ui-json>` tags.

### 1.1 Message Structure

Every A2UI v0.9 message is stamped with `"version": "v0.9"`.

There are 4 server-to-client message types:

1. **`createSurface`**: Initializes a UI surface with the target catalog.
   ```json
   {
     "version": "v0.9",
     "createSurface": {
       "surfaceId": "analysis-summary",
       "catalogId": "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"
     }
   }
   ```
   > [!IMPORTANT]
   > `createSurface` has **NO `root` key** in v0.9. The root component in `updateComponents` MUST have `id: "root"`.

2. **`updateComponents`**: Delivers the component tree.
   ```json
   {
     "version": "v0.9",
     "updateComponents": {
       "surfaceId": "analysis-summary",
       "components": [
         {
           "id": "root",
           "component": "MaterialCard",
           "children": ["mainCol"]
         },
         {
           "id": "mainCol",
           "component": "MaterialColumn",
           "children": ["title", "div1", "table1", "btnRow"]
         }
       ]
     }
   }
   ```

3. **`updateDataModel`**: Updates reactive client state.
   ```json
   {
     "version": "v0.9",
     "updateDataModel": {
       "surfaceId": "analysis-summary",
       "path": "/filters",
       "value": { "selectedCategory": "Electronics", "minScore": 85 }
     }
   }
   ```

4. **`deleteSurface`**: Dismisses or clears a surface.
   ```json
   {
     "version": "v0.9",
     "deleteSurface": {
       "surfaceId": "analysis-summary"
     }
   }
   ```

---

## 2. Key Differences: v0.8 vs v0.9

| Feature | A2UI v0.8 | A2UI v0.9 (Current Standard) |
|---|---|---|
| **Wire Version** | N/A | `"version": "v0.9"` (stamped on every message) |
| **Surface Creation** | `{"beginRendering": {"surfaceId", "root": "root"}}` | `{"version": "v0.9", "createSurface": {"surfaceId", "catalogId"}}` |
| **Root Component** | Specified in `beginRendering.root` | Must have `id: "root"` |
| **Component Syntax** | `{"id": "...", "component": {"Text": {...}}}` (wrapped) | `{"id": "...", "component": "MaterialText", "text": "..."}` (flat) |
| **Literal Strings** | `{"literalString": "Hello"}` | `"Hello"` (plain JSON strings) |
| **Children List** | `{"children": {"explicitList": ["a", "b"]}}` | `{"children": ["a", "b"]}` (plain arrays) |
| **Button Labels** | Required separate `Text` component via `child: "text_id"` | Flat `label: "Click Me"` on `MaterialButton` |
| **Button Actions** | `{"action": {"name": "sendText", "context": [{"key", "value"}]}}` | `{"action": {"event": {"name": "...", "context": {"prompt": "..."}}}}` |
| **Client Press** | Arrived as `TextPart` (`{"userAction": ...}`) | Arrives as `DataPart` (`{"version": "v0.9", "action": ...}`) |
| **Data Tables** | Faked with nested `Row` / `Column` | Native `MaterialTable` / `GcbpTable` |
| **Charts** | Faked with generated PNG images | Native `VegaChart` (interactive JSON spec) |
| **Dashboards** | Faked with external URL in new browser tab | Native `IFrameSrcdoc` (sandboxed inline iframe) |
| **Reports** | Streamed as long markdown text | Native `Canvas` (interactive side panel) |

---

## 3. Core Component Library

### 3.1 MaterialCard
```json
{
  "id": "root",
  "component": "MaterialCard",
  "children": ["main_column"]
}
```
> [!IMPORTANT]
> `MaterialCard` requires **`children`** (an array), and the catalog's schema does not
> define `child` on it at all. `child` is a single-id property of the *non-Material*
> `Card`, `Button` and `Tabs` components, and writing it on a `MaterialCard` gives the
> surface a schema-foreign property — which is enough for the renderer to drop the whole
> thing, since it is strict where draft-07 validation is lenient.

### 3.2 MaterialColumn & MaterialRow
```json
{
  "id": "main_column",
  "component": "MaterialColumn",
  "children": ["title_text", "divider1", "kpi_row"],
  "justify": "start",
  "align": "stretch"
}
```

### 3.3 MaterialButton (Action & Navigation)
```json
{
  "id": "btn_approve",
  "component": "MaterialButton",
  "label": "Approve and run",
  "variant": "filled",
  "action": {
    "event": {
      "name": "approve_workflow_execution",
      "context": {
        "prompt": "Approve this and run the workflow",
        "actionId": "ACT-8492"
      }
    }
  }
}
```
> [!NOTE]
> `context.prompt` is the exact message Gemini Enterprise displays as what the user said when clicking the button.

### 3.4 MaterialTable (Native Data Presentation)
```json
{
  "id": "summary_table",
  "component": "MaterialTable",
  "columns": [
    {"header": "Site", "field": "site"},
    {"header": "Current", "field": "current"},
    {"header": "Threshold", "field": "threshold"},
    {"header": "Status", "field": "status"}
  ],
  "rows": [
    {"site": "Site A", "current": "1,240", "threshold": "1,500", "status": "⚠️ Below threshold"},
    {"site": "Site B", "current": "3,890", "threshold": "2,000", "status": "✅ Healthy"},
    {"site": "Site C", "current": "850", "threshold": "1,200", "status": "🚨 Action required"}
  ]
}
```

> [!IMPORTANT]
> Columns are objects, not header strings, and each row is keyed by `field` —
> not a positional array. There is no `headers` property.

### 3.5 VegaChart (Native Interactive Visualizations)
```json
{
  "id": "revenue_trend_chart",
  "component": "VegaChart",
  "spec": {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "description": "Monthly Performance Trend",
    "data": {
      "values": [
        {"month": "2026-04", "amount": 120},
        {"month": "2026-05", "amount": 145},
        {"month": "2026-06", "amount": 190}
      ]
    },
    "mark": "bar",
    "encoding": {
      "x": {"field": "month", "type": "ordinal", "title": "Month"},
      "y": {"field": "amount", "type": "quantitative", "title": "Amount"}
    }
  }
}
```

### 3.6 Suggestion Chips (At the End of Responses)

**One chip bar per response, and it is always its own surface.** Emit the standalone
`suggestions` surface below at the end of EVERY normal response — never as a trailing
`MaterialRow` inside the card. The welcome card is the one exception: its buttons are
its own content, not follow-up chips.

This used to say the opposite, on the theory that "Gemini Enterprise renders only the
FIRST A2UI surface of a turn". That is wrong on both halves. A turn's second surface
does render (a marker surface plus a card, 2026-08-23, both visible), and what failed
in v11.68 was a chip bar on the reserved surfaceId `suggestions` specifically, which
the server now scopes per turn.

**Where a button sits does NOT decide where a press leaves the reader.** Six rounds of
layout fixes (v11.83-v11.89) assumed it did. The test that settled it changed nothing in
the agent: press a button in the newest turn, then scroll up and press one in a much
older turn — the view jumps DOWN, onto the surface pressed a moment earlier. **On a
press, Gemini Enterprise scrolls to the element of the user's PREVIOUS press.** No rule
about "the surface above the pressed one" can scroll downward, so all of them are
withdrawn, including the two this file used to state.

The anchor is client state and nothing the agent emits can move it. What v11.90 does
instead is delete the surface the press came from
(`_pressed_surface_delete_parts` in `fast_api_app.py`), so the anchor the NEXT press
uses no longer exists. Kill switch: `A2UI_KEEP_PRESSED_SURFACE=1`.

The layout the code still produces is kept on its own merits, not as a scroll fix:
chips in their own trailing surface, card-wrapped by `_card_wrap_chip_surface` (styled
`border: none` / `background: transparent`, so it looks unchanged), and gate cards
whose fields and buttons ship below the card via `_action_surface_parts()`. The fields
move with the buttons because a `{"path": ...}` binding is resolved against the surface
the button lives in, not the turn.

That is also the one case where buttons stay INSIDE a card: a compose, confirmation or
what-if card whose button reads the card's own bound fields cannot be split. Give those
a footer — the main `MaterialColumn` ends with exactly two children, a `MaterialDivider`
and then the button row, and nothing follows the row.

An invisible trailing "landing" surface does not work as a substitute (v11.88 tried a
transparent card holding a zero-width space): it is emitted but never drawn, and GE has
never been seen to render a component tree with no text in it (v10.68).

```json
{"id": "mainCol", "component": "MaterialColumn",
 "children": ["title", "table", "summary", "footerDivider", "actionRow"],
 "justify": "start", "align": "stretch", "style": {"gap": "10px"}},
{"id": "footerDivider", "component": "MaterialDivider"},
{"id": "actionRow", "component": "MaterialRow", "children": ["b1", "b2", "b3"],
 "justify": "spaceEvenly", "align": "center", "style": {"gap": "8px", "marginTop": "8px"}}
```

```json
<a2ui-json>[
  {"version": "v0.9", "createSurface": {"surfaceId": "suggestions", "catalogId": "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"}},
  {"version": "v0.9", "updateComponents": {"surfaceId": "suggestions", "components": [
    {"id": "root", "component": "MaterialRow", "children": ["chip1", "chip2", "chip3"]},
    {"id": "chip1", "component": "MaterialButton", "label": "📊 Run a detailed analysis", "action": {"event": {"name": "run_detail_analysis", "context": {"prompt": "Run a detailed analysis"}}}},
    {"id": "chip2", "component": "MaterialButton", "label": "📝 Draft the follow-up record", "action": {"event": {"name": "create_record", "context": {"prompt": "Draft the follow-up record"}}}},
    {"id": "chip3", "component": "MaterialButton", "label": "📈 Forecast the weekly trend", "action": {"event": {"name": "forecast_trend", "context": {"prompt": "Forecast the weekly trend"}}}}
  ]}}
]</a2ui-json>
```

---

## 4. Onboarding Welcome Card (Turn 1 Guardrail)

On the very first user greeting turn (any greeting, in any language):
1. Agent **MUST NOT call any tools or databases**.
2. Agent outputs **ONE line of plain text greeting** in the user's language.
3. Agent outputs the rich onboarding card using `surfaceId: "welcome-card"` with 3 action buttons.
4. Agent does **NOT** append suggestion chips on Turn 1 (the welcome card buttons are sufficient).

```json
All bracketed placeholders below are filled from the demo's own domain, and written
in the conversation language - never carry another demo's wording into a new one.

<a2ui-json>[
  {"version": "v0.9", "createSurface": {"surfaceId": "welcome-card", "catalogId": "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"}},
  {"version": "v0.9", "updateComponents": {"surfaceId": "welcome-card", "components": [
    {"id": "root", "component": "MaterialCard", "children": ["mainCol"]},
    {"id": "mainCol", "component": "MaterialColumn", "children": ["title", "div1", "capCol", "div2", "actionsRow"]},
    {"id": "title", "component": "MaterialText", "text": "<greeting naming the company and what this agent does>", "usageHint": "h2"},
    {"id": "div1", "component": "MaterialDivider"},
    {"id": "capCol", "component": "MaterialColumn", "children": ["cap1", "cap2", "cap3"]},
    {"id": "cap1", "component": "MaterialText", "text": "🔍 <capability 1: what it can analyze across the demo's data>", "usageHint": "body"},
    {"id": "cap2", "component": "MaterialText", "text": "📑 <capability 2: what it reconciles against the external documents>", "usageHint": "body"},
    {"id": "cap3", "component": "MaterialText", "text": "⚡ <capability 3: what it can act on and remediate>", "usageHint": "body"},
    {"id": "div2", "component": "MaterialDivider"},
    {"id": "actionsRow", "component": "MaterialRow", "children": ["act1", "act2", "act3"]},
    {"id": "act1", "component": "MaterialButton", "label": "📊 <opening question 1>", "action": {"event": {"name": "check_daily_alerts", "context": {"prompt": "<the same question, phrased as the user would type it>"}}}},
    {"id": "act2", "component": "MaterialButton", "label": "🔍 <opening question 2>", "action": {"event": {"name": "inspect_anomalies", "context": {"prompt": "<the same question, phrased as the user would type it>"}}}},
    {"id": "act3", "component": "MaterialButton", "label": "📄 <opening question 3>", "action": {"event": {"name": "audit_reports", "context": {"prompt": "<the same question, phrased as the user would type it>"}}}}
  ]}}
]</a2ui-json>
```
