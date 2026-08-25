# Accessibility contract — Universality Index Tool (UI band)

**Status: design contract — implemented 2026-08-26 (`ui/app.py` + `ui/ui_model.py`); this document remains binding. Flagged deviations are recorded in `UI_ARCHITECTURE.md` §4.1 and `docs/changelog.md` (2026-08-26).**
Companions: `DESIGN_SYSTEM.md`, `UI_ARCHITECTURE.md`, `UX_FLOW.md`.

## 1. Target and method

- **WCAG 2.1 AA** is the acceptance bar. The page is a document-like single column, which keeps the a11y surface small and auditable.
- The implementation must pass: (a) an axe-core (or equivalent) automated scan with zero AA violations in the pinned Streamlit version's DOM (including the injected CSS layer), and (b) the manual checklist in §8 (keyboard pass + screen-reader pass on the two reference scenarios: happy path TV7, and the E2 weight-sum error).
- Screen-reader support target: NVDA + JAWS (Windows) and VoiceOver (macOS/iOS) — the two platforms where real Baskerville renders (see `DESIGN_SYSTEM.md` D-UI-1) get first-class review; fallback-stack platforms must still pass AA.

## 2. Language, landmarks, structure

- `<html lang="en">` (Streamlit page config `page_language` / document head).
- **Heading outline (exactly):**
  - `h1` — "Universality Index Tool" (masthead wordmark; the single h1).
  - `h2` — "Part I — Evaluation setup" · "Part II — Parameters" · "Part III — Results" (present in the DOM **before** the first calculation, so landmarks are stable).
  - `h3` — inside results: "Overall index" · "Group indices" · "User-group gap" · "Per-parameter details". Group stat cards use **bold text, not headings** (they are stats, not sections).
- **Landmarks:** one main region (the whole page); the error summary is a `role="alert"` region (see §6); the footer disclaimer is a `contentinfo`-style region (or plain text — not a landmark) to avoid landmark noise.
- **Skip link:** first focusable element, visually hidden until focused: "Skip to calculation" → focuses the Calculate button (essential on 100-parameter pages).
- Table: real table semantics — `caption` ("Per-parameter normalized scores (s ÷ scale)"), `th scope="col"` headers, `th scope="row"` for parameter names; contributions table (when expanded) has its own caption. Never a div-grid masquerading as a table.

## 3. Forms

- **Every field has a visible, programmatically associated label** (`<label for>` / framework equivalent): "Product name", "Scale maximum", "Name of parameter {n}" (visible: "Name" with the card heading "Parameter {n}" as the group context — the card heading is an `aria-labelledby` source), "Weight", "FAP score", "SAP score", "DAP score" (the **full** strings are the accessible names even where the visible micro-label is the abbreviation — D-UI-8).
- **Placeholders never carry meaning**: placeholders are examples only ("e.g., Accessible chair"); the required-ness is conveyed by the gate's error, and the label is always visible.
- **Input modes:** numeric fields accept typing of the full decimal (spinner step is convenience); integer-only fields (scale) — if the framework allows typing 5.0, the gate rejects (V11) with the verbatim message; the UI does not pre-block it.
- **Error association (normative):** each field in error gets `aria-invalid="true"` and `aria-describedby` pointing at its inline error element (which also carries the translated label). The error summary panel is `role="alert"` (assertive) and is reached by focus order *before* the first offending field (it renders at the top of the affected part).
- **Focus management on Calculate failure:** focus moves to the error summary panel (`tabindex="-1"`, programmatic). From there the user Tabs to the first offending field (the panel sits immediately above it in DOM order).
- **Focus management on success:** focus moves to the Part III heading (programmatic), so screen-reader users hear "Part III — Results" and then the figures.
- **Group labels:** FAP/SAP/DAP are defined once in the first parameter card's legend ("FAP — Fully Abled People · SAP — Specially Abled People · DAP — Differently Abled People"); subsequent cards' accessible names still use the full form ("Fully Abled People (FAP) score of parameter 2") so the definition is not positional.

## 4. Color and contrast (measured against DESIGN_SYSTEM tokens)

| Pair | Ratio | Requirement |
|---|---|---|
| `--ink` #111827 on `--bg-card` #FFFFFF | 15.9:1 | ≥ 4.5:1 ✅ |
| `--ink-2` #4B5563 on #FFFFFF | 7.5:1 | ≥ 4.5:1 ✅ |
| `--ink-2` on `--bg-blue-wash` #EAF1FB | 6.6:1 | ≥ 4.5:1 ✅ |
| `--ink` on `--bg-blue-wash` | 14.4:1 | ✅ |
| White on `--brand-700` #1D4ED8 (primary button) | 6.7:1 | ≥ 4.5:1 ✅ |
| `--brand-700` on #FFFFFF (links, secondary text accents) | 6.7:1 | ✅ |
| `--err-700` #B91C1C on `--err-50` #FEF2F2 | 5.9:1 | ≥ 4.5:1 ✅ |
| `--ok-700` #15803D on #FFFFFF | 5.0:1 | ✅ |
| `--ink-disabled` #9CA3AF on #F3F4F6 (disabled) | 2.4:1 | WCAG 1.4.3 **exempt** (disabled controls) — documented, not a pass |
| Grid pattern vs paper | decorative, 6% opacity | 1.4.3 exempt (background); verified it does not reduce adjacent text below the above ratios when rendered behind opaque cards |

- **Color is never the only channel:** error = icon + text (not just red); success = "✓ Calculated" text; disabled = greyed **and** non-interactive **and** `aria-disabled`; group distinction = text labels (no group colors exist — `DESIGN_SYSTEM.md` §2.3).
- **Focus visibility:** 2px `--brand-600` outline with 2px offset on every interactive element (buttons, inputs, skip link, table expand control); `outline` never `none`/`transparent`. The focus ring is the only glow on the page (no competing shadows).
- **Hit targets:** ≥ 44×44 CSS px for buttons and the × icon (padding achieves it); table row text is ≥ 14px with 20px line-height.
- **Text scaling:** the layout must survive 200% browser zoom without loss of content or function (no fixed-height containers that clip; `max-width` in `rem`; the 880px column scales). Font sizes in the design system are the *initial* values.

## 5. Keyboard

| Control | Keys |
|---|---|
| Skip link | Tab (first stop) → Enter |
| Text/number inputs | full typing; spinners respond to arrows (framework default); labels focusable-with-input (single tab stop per field) |
| Calculate / Reset / Add / Reset weights / × | Tab-reachable in visual order; Enter/Space activates |
| Error summary | focusable (`tabindex="-1"` — programmatic only, not in tab order) |
| Results table | rendered as native table → arrow-key navigation where the platform supports it; no custom grid navigation required |
| Contributors: no keyboard trap anywhere; `Escape` is not used for anything (no modals exist) |

Focus order = DOM order = visual order (single column guarantees the three coincide; the error panel is inserted at the top of its part, keeping the invariant).

## 6. Live regions and announcements

| Region | Type | Content |
|---|---|---|
| Error summary panel | `role="alert"` (assertive) — announced on appearance | verbatim gate message + field list |
| Calculation status | `aria-live="polite"` (a visually-hidden mirror of the button state) | "Calculating…" → "Calculated" or "Calculation failed" |
| Parameter counter | `aria-live="polite"` | "3 of 100" updates on add/remove |
| Weight-reset confirmation | not live (the button label change is visible; SR users re-focus the button) | — |

Exactly these three live regions. Nothing else announces (calm = quiet; the results themselves are read when focus arrives).

## 7. Motion and sensory

- `prefers-reduced-motion: reduce` → all transitions/fades are instant, scroll-into-view becomes a jump, the indeterminate progress line is replaced by the static "Calculating…" label only.
- No autoplaying content, no flashing (the progress line is a solid slow fill, < 3 flashes/sec trivially satisfied), no sound.
- `prefers-contrast: more` is honored by darkening `--ink-2` usage to `--ink` (single CSS media query; the palette has headroom for this).

## 8. Manual acceptance checklist (run in both reference scenarios)

**Scenario A — happy path (TV7 raw):**
1. [ ] New tab: SR reads "Universality Index Tool, heading level 1", then the purpose line.
2. [ ] Tab order: skip link → Reset (masthead) → product → scale → Parameter 1 name → weight → FAP → SAP → DAP → Add → Reset weights → Calculate → (footer). No surprises.
3. [ ] Enter the TV7 values; each field announces its label on focus ("Product name, edit text").
4. [ ] Enter Calculate: "Calculating…" announced (polite); after ≤ 1s, focus lands on "Part III — Results, heading level 2"; the overall figure is read with its label ("Universality Index (UI): 0.5533").
5. [ ] Table: SR reads the caption, then row headers and columns in reading order; numeric values read with 4 decimals.
6. [ ] 200% zoom: no clipped fields, no lost content, focus ring fully visible.

**Scenario B — error path (weight sum 0.96, E2):**
7. [ ] Enter TV7 values but leave one weight at 0.26; Calculate.
8. [ ] The alert region is announced: "Please check the highlighted field. Invalid weights: parameter weights must sum to 1." (verbatim gate message).
9. [ ] Focus is on the alert; one Tab reaches the Part II header region (list-level error).
10. [ ] Fix the weight, Calculate: "Calculated" announced; results replace; the stale-results caption is gone.
11. [ ] axe scan on the error state: zero AA violations (including the error elements' contrast and `aria-invalid` wiring).

## 9. Streamlit-specific notes (flagged)

- Streamlit's default focus styles and label association vary by version: the injected CSS layer must (a) keep `outline` visible on `[data-testid="stTextInput"] input` / `input[type=number]` and (b) the label-association pattern of the pinned version must be verified in the scenario pass. If a pinned version cannot associate labels programmatically, the field's accessible name falls back to `aria-label` set via the framework's `label_visibility`/accessibility parameters — the behavioral contract (label announced, associated, visible) is invariant.
- `role="alert"` and `aria-live` are realized via the framework's built-in `st.error` semantics where they match, else via the `st.markdown(unsafe_allow_html=True)` wrapper with explicit ARIA attributes (static attributes, no user data).
- The skip link is injected HTML at the top of the main region (Streamlit renders the first `st.markdown` first; the link's target is the Calculate button's DOM id probed at render time).
