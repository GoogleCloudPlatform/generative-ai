# Frontend component guide

Rules for every Lit element in `frontend/src`. They are written to be checkable:
most are enforced by `npm run lint`, `npm test`, or `npm run manifest:check`
(all run by `make lint` / `make test`). When a rule and the code disagree, fix
one of them in the same change.

## 1. Tiers

| Tier                | Where                                                                                              | What it may do                                                                                                                           |
| ------------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 1 Primitives        | `src/components/ui/ga-*.ts`                                                                        | Generic, app-agnostic controls. No domain imports (`domain/`, `store`), no `fetch`, no media APIs.                                       |
| 2 Domain components | `src/components/avatar/`, `src/components/live/`, `src/components/session/` (shared by both modes) | Compose primitives for one feature. Receive data via properties, report intent via events. No `fetch`, no WebSockets, no `Store` writes. |
| 3 Views             | `my-element.ts`, `*-setup.ts`, `*-session.ts`, `app-settings.ts`                                   | Own state, I/O (fetch, WebSocket), controllers and routing.                                                                              |

Long-lived resources (media streams, AudioContext, MSE, timers, sockets,
keyboard models) live in `ReactiveController`s under `src/controllers/`, and
release everything in `hostDisconnected()`.

## 2. Elements

- **Light DOM.** Every element overrides `createRenderRoot() { return this; }`
  so Tailwind classes and document-level IDs work. Consequence: an element
  must not rely on light-DOM children of its host. Pass content as properties
  (strings, option arrays), not as children or `<slot>`s.
- **Registration.** `@customElement('ga-thing')` and a matching
  `HTMLElementTagNameMap` entry in the same file.
- **Naming.** Tags: `ga-*` (Tier 1), `avatar-*` / `live-*` / `session-*`
  (Tier 2). Filename = tag name. One element per file (`ga-status-dot` in
  `ga-badge.ts` is a legacy exception).
- **Docs.** The class JSDoc states what the element is for and lists every
  event with `@fires name - when. Detail: {...}`. Public properties that are
  not self-explanatory get a one-line JSDoc. `custom-elements.json` is
  generated from this; run `npm run manifest` and commit the result.

## 3. Properties and attributes

- Attributes are kebab-case: `@property({ attribute: 'supporting-text' }) supportingText`.
  Never rely on HTML lower-casing a camelCase name (`?isProcessing=`).
- Reflect (`reflect: true`) only properties that styling or tests select on
  (`variant`, `size`, `disabled`, `checked`, `appearance`).
- Objects and arrays use `attribute: false` and are bound with `.prop=`.
- Do not name properties after `HTMLElement` members (`title`, `hidden`,
  `ariaLabel`, `role`, `tabIndex`) unless intentionally overriding them.
  Use `heading`, `accessible-label`, `badge-title` instead.

## 4. Events

- **Names:** primitives emit `ga-*` (`ga-change`, `ga-action`); Tier 2 emits
  `<feature>-<verb>` (`avatar-generate`, `session-action`); views emit
  plain domain names (`connect`, `disconnect`).
- **Shape:** `new CustomEvent<Detail>(name, { detail, bubbles: true, composed: true })`
  with a named detail type exported next to the element (or `GaChangeDetail`
  for `ga-change`). Add every event to `HTMLElementEventMap`.
- **Only on user action.** Setting a property programmatically never fires an
  event. Fire once per user action (no `input` + `change` duplicates).
- **No re-emitting.** In Light DOM a child's `ga-change` already bubbles
  through its parent. A thin wrapper either lets it bubble unchanged
  (`avatar-preset-picker`) or stops it and emits its own domain event
  (`avatar-prompt-generator` → `avatar-prompt-change`,
  `avatar-upload-studio` → `avatar-transform-mode-change`). Never both.
- **Native `click`** is the action event for `ga-button`; it is not re-dispatched.

## 5. Colour, type and theme

- `src/theme/tokens.ts` is the only palette (light and dark). Run
  `npm run tokens` after editing it; a test fails if `tokens.css` is stale or if
  the themes define different keys.
- Use token utilities (`bg-surface-container`, `text-on-surface-variant`,
  `border-outline-variant/30`). No hex/`rgb()` literals and no Tailwind default
  palette colours (`slate-*`, `sky-*`, `black`) in components. Canvas code uses
  `colorTokenReader(this)`. Lint enforces the literal rule.
- `primary` (#4285F4, the brand blue) is for solid fills and accents. Primary
  coloured text and links use `text-primary-text`, which meets AA on every
  surface. Do not use `outline` for text; use `on-surface-variant`.
- Text pairs follow `on-X` on `X` and must meet WCAG AA (4.5:1); the token test
  checks every pair. The only accepted exception is white on the solid brand
  fills (`primary`, `success`, `nav`), a deliberate brand decision listed in
  `tokens.test.ts` and `src/test/fixture.ts`.
- Themes: `data-theme="light" | "dark" | "system"` on `<html>`, chosen in
  Settings → Global Preferences (`AppSettings.theme`, default light) and applied
  by `<my-element>` (plus a pre-paint snippet in `index.html`). Dark mode
  passes axe with no exceptions.
- Theme-aware roles: `primary-soft` / `on-primary-soft` for selected tiles,
  icon chips and tonal hovers; `nav` / `on-nav` for the sidebar and mobile
  header; `media-backdrop` behind camera/video previews. Do not use the M3
  `*-fixed` or `inverse-*` tokens for surfaces that should follow the theme
  (they are deliberately constant, or invert); `inverse-*` is fine for toasts.

## 6. Accessibility

- **Names:** every form control has a label. Primitives link `<label for>` to
  their control with `uniqueId()`; use `hide-label` instead of omitting `label`.
  Icon-only buttons set `accessible-label`.
- **Descriptions and errors:** supporting text, counters and errors are linked
  with `aria-describedby`; errors also set `aria-invalid`.
- **State:** on/off buttons use `toggle` (`aria-pressed`); single choice uses
  `ga-radio-group` (`role="radio"`, `aria-checked`); tabs use
  `ga-segmented-control`.
- **Keyboard:** composite widgets use `RovingFocusController`: one tab stop,
  arrows move (mirrored in RTL), Home/End jump, selection follows focus for
  radios and tabs. Space/Enter activate.
- **Live regions** exist before content is added (`ga-toast-region` keeps
  both its `status` and `alert` regions rendered). Do not put `aria-live` on
  rapidly streaming text.
- **Motion:** honour `prefers-reduced-motion` (handled globally in
  `index.css`); animated canvases must still update state without animating.
- **No blocking dialogs:** use `showToast()`, never `alert`/`confirm`/`prompt`
  (lint enforces this).

## 7. Primitive catalogue

| Tag                         | Use for                                                                  |
| --------------------------- | ------------------------------------------------------------------------ |
| `ga-button`                 | Every button. `variant`, `size`, `icon`, `loading`, `toggle` + `active`. |
| `ga-field`                  | Text, number and multi-line inputs with label, counter, error.           |
| `ga-select`                 | Native select with label and supporting text.                            |
| `ga-checkbox`               | Labelled checkbox; `appearance="card"` for feature toggles.              |
| `ga-radio-group`            | Single choice; `appearance` is `chip`, `tile` or `card`.                 |
| `ga-segmented-control`      | Tabs that switch a panel.                                                |
| `ga-section-header`         | Page and settings-section headings with an optional action.              |
| `ga-badge`, `ga-status-dot` | Status labels.                                                           |
| `ga-toast-region`           | App-level notifications (`showToast()`).                                 |
| `renderIcon()`              | Inline SVG icons from `icons.ts`.                                        |

Shared session pieces (Tier 2, `src/components/session/`, used by both
`/` avatar and `/live` sessions):

| Tag / helper               | Use for                                                                    |
| -------------------------- | -------------------------------------------------------------------------- |
| `session-stage-header`     | Status dot, voice (or mute toggle with `mute-toggle`), serving model.      |
| `session-control-bar`      | Message input + camera / screen / end / mic controls.                      |
| `session-transcript-panel` | Transcript log (`role="log"`, `aria-busy` while streaming) and info cards. |
| `renderPipPreview()`       | Camera / screen-share picture-in-picture inside a stage.                   |

Session components report user intent with one event, `session-action`
(`{ action: 'toggle-mic' | 'toggle-camera' | 'toggle-screen' | 'toggle-mute' | 'end-session' }`),
plus `session-send-text` (`{ text }`). Views switch on `detail.action`.

Add a primitive only when it replaces markup repeated in at least two places
or fixes an accessibility gap. Each primitive ships with a
`ga-<name>.test.ts` covering its accessible name, keyboard behaviour, events
(including "no event on programmatic change"), and an `expectAccessible()`
check.

## 8. Tests and tooling

```bash
cd frontend
npm run lint              # eslint (lit, wc, token and dialog rules) + tsc --strict
npm test                  # Vitest in headless Chromium (CHROMIUM_PATH=/usr/bin/chromium if no Playwright browser)
npm run manifest:check    # custom-elements.json is current
npm run tokens            # regenerate src/theme/tokens.css
```

Test helpers live in `src/test/fixture.ts`: `fixture()`, `settle()`,
`recordEvents()`, `expectAccessible()` (axe, WCAG 2.1 A/AA).
