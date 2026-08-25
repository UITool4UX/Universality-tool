# UI architecture — Universality Index Tool (UI band)

**Status: design contract — implemented 2026-08-26 (`ui/app.py` + `ui/ui_model.py`); this document remains binding. Implementation notes and flagged deviations: §4.1 below and `docs/changelog.md` (2026-08-26).**
Companions: `DESIGN_SYSTEM.md` (visual contract), `UX_FLOW.md` (behavior + copy), `ACCESSIBILITY.md` (a11y contract).
Upstream: `architecture.md` §5–§6 (imports), §16 (UI notes), `validation-and-security.md` (error contract), `FORMULA_SPECIFICATION.md` (A6).

## 1. Scope and hard boundaries (re-stated, binding)

- The UI is the **composition root**: it collects primitives, calls the Application layer, and renders. It contains **no math** — no formula, no tolerance comparison, no summing, no rounding, no clamping, no coercion. Its only numeric literals are display conveniences (spinner steps, min/max hints) and formatting strings.
- Imports: **`universality` package public API only** (`from universality import …`), plus the Application module `universality.services` when it exists. Never `universality.domain` / `calculation` / `validation` submodules directly.
- Streamlit is the only framework (finalized architecture). No other runtime dependencies; no npm; no build step. Self-hosted font files (Lora, SIL OFL) live under `ui/` as static assets.
- Server-side validation (`validate`) is the **sole authority** for input correctness. UI bounds and hints never replace it.
- The UI must display: declared scale (A3), parameter weights with the 1/n default (A2), group weights 1/3 each (A1 — imported from the public API, **never hardcoded**), results via `format_for_display` (A6), the as-given-scores note (A4), and the A7 statement (simplified implementation, not a full reproduction of the research methodology).
- Single page. No routes, no nav bar, no accounts, no persistence (M8), no export (V15-gated), no multi-evaluation state.
- Servers bind `0.0.0.0`; no host/origin allowlist may reject the preview host.

## 2. Framework mapping and flagged constraints

The visual contract in `DESIGN_SYSTEM.md` is specified **component/semantic-first**; the table below maps every element to the Streamlit mechanism that will realize it, with an honesty rating. **Flagged decision (D-UI-3):** Streamlit does not natively expose per-widget state styling; three elements are therefore realized by *adjacent elements* rather than widget restyling, and CSS overrides of Streamlit internals are **version-fragile** (they depend on Streamlit's DOM/classes). Each fragile override is best-effort and non-normative: if a Streamlit upgrade breaks an override, the *behavioral* contract (inline error under the field, visible focus, disabled look) still holds via the adjacent-element pattern.

| Design element | Streamlit realization | Fragility |
|---|---|---|
| Fonts (Lora self-hosted; Baskerville stack) | `<style>` block injected once at script top via `st.markdown(unsafe_allow_html=True)` with `@font-face` (relative asset URLs served from `ui/` by the app server) + CSS custom properties on `:root` | Low (CSS-only) |
| Page background (paper + 6% grid) | CSS on `section[data-testid="stMain"]` / body: `background-color: var(--bg-paper)` + two 24px linear-gradients in `rgba(29,78,216,0.06)` | Low–medium (target selector varies by version → probe a few known selectors; pattern degrades gracefully to plain paper) |
| Card / panel / color blocking | `st.container` + CSS classes via `st.markdown` wrapper HTML **or** styled `st.container(border=True)` (version-dependent) with class hooks; fallback: markdown-HTML section wrappers (content is framework-safe; see §7) | Medium |
| 4–7px radius, borders, hairlines | CSS overrides on `.stMarkdown`, `[data-testid="stContainer"]`, form elements | Medium |
| Primary button | `st.button("Calculate", type="primary")` + CSS to match tokens | Low |
| Secondary / tertiary buttons | `st.button` + CSS class differentiation (secondary: outlined via CSS; tertiary: borderless; add-parameter: dashed). **No native variant API** — CSS is the mechanism | Medium |
| Inputs (default/focus/disabled) | `st.text_input` / `st.number_input`; focus & disabled look restyled via CSS | Low–medium |
| **Field-level error state** | **Adjacent pattern (normative):** the gate's message rendered as `st.error(..., icon="warning")` **immediately under the offending field** inside the field's column, plus the error summary panel (`st.error`, `role="alert"` via `aria` mapping in `ACCESSIBILITY.md`). Best-effort (non-normative): border color on the input via CSS hook | Behavioral contract is robust; exact "red border" is best-effort |
| Success state | Section-level only: results section + "Calculated ✓" caption (`st.success` restyled to the calm `--ok-700` rule) — no per-field success (D-UI-2) | Low |
| Loading state | Button disabled + label "Calculating…" + thin 2px progress line element below the button (CSS-styled `st.progress(0.5)` or a styled div) | Low |
| Result figures | Plain `st.text` / styled HTML text nodes — **never** `st.metric` (KPI-card look is out of the design language) | Low |
| Parameter table | Baseline: `st.dataframe` (escapes by default; styled via CSS). Alternative (documented, requires the §7 escaping rule): hand-built HTML `<table>` via `st.markdown(unsafe_allow_html=True)` with `html.escape()` on every user string | Low (dataframe) / Medium (HTML table) |
| Group weights display | `SIMPLE_MODE_GROUP_WEIGHTS` from the public API, rendered via `format_for_display` — e.g. "W = 0.3333 each (1/3, Simple Mode — shown, not editable)" | Low |
| Two-click Reset (no modal) | `reset_armed` session flag + button label swap ("Reset evaluation" → "Confirm reset — clears all entered data?") with 5s auto-disarm | Low |

**Option B (documented, NOT approved):** if, during the UI task, the CSS-override fragility proves unacceptable in the pinned Streamlit version, the documented fallback is a minimal vanilla HTML/CSS/JS single page (no framework, no build step; the Streamlit server is replaced by the Application layer exposed over a small stdlib HTTP boundary). Option B is a **change-control item** (`architecture.md` "no new frameworks" clause) requiring explicit approval; all four design documents remain valid under Option B because they are component/semantic-first. The default path is the Streamlit mapping above.

## 3. Page structure (mirrors `UX_FLOW.md` wireframe)

```
ui/app.py            # composition root — render order:
  render_masthead()          # wordmark, purpose line, version + Simple Mode tag, Reset (secondary)
  render_part1_setup()       # product name, scale maximum
  render_part2_parameters()  # parameter cards, Add (tertiary), Reset weights (tertiary), Calculate (primary)
  render_part3_results()     # absent/placeholder | success | dimmed-previous on error
  render_footer()            # A4 + A7 notes, method line
  collect_raw() -> dict      # assembles the raw schema (assembly only — no math)
  apply_error(rejection)     # path → field targeting (pure mapping, §5)
```

## 4. Input collection and the "no silent modification" rule

- Widgets bind to **session-state keys**: `product` (str), `scale_max` (int), and per parameter `p{i}_name` (str), `p{i}_weight` (float), `p{i}_fap|sap|dap` (float/None-erased). `collect_raw()` reads the keys in index order and assembles exactly the documented raw schema — `{"product", "scale_max", "parameters": [{"name","weight","scores":{"fap","sap","dap"}}]}`. Unknown keys are never added. This is *assembly*, not computation: it is the only place the UI shapes data, and it is covered by unit tests (pure function over a fake state dict).
- **Defaults (visible, editable — flagged decision D-UI-4):** fresh form = 1 parameter; `scale_max = 5` (number inputs cannot be blank; 5 is the common 1–5 Likert maximum — shown and changeable); parameter weight `1.0` (the true 1/n default for n = 1); each score `1` (the user-input minimum, A20). Every default is *displayed in the field* — nothing is hidden. The gate remains authoritative for everything.
- **Adding a parameter** appends a card with weight **0.0** and score defaults; it **never redistributes existing weights** (D-UI-5 — no automatic modification of entered data). The 1/n default is offered explicitly: "Reset weights to 1/n" (tertiary) sets every weight to `1.0 / n` (this is presentation arithmetic on *default values*, computed as `1.0 / n` at click time — flagged as the UI's single permitted arithmetic operation, a division by the displayed parameter count; it writes defaults, not fixes, and the gate still validates C1).
- **Removing a parameter** deletes that card's keys and re-indexes; disabled at n = 1 (mirrors V12); no confirmation (flagged: v0.1 accepts the small re-entry cost over modal friction — revisit if feedback disagrees).
- **Reordering is not offered (D-UI-6):** entry order = display order = the engine's deterministic summation order. A reorder control would silently change bit-exact FP results (summation order) — the tool treats entry order as the student's ordering.
- **Changing `scale_max`** never touches stored scores (no silent modification). Over-scale scores surface on Calculate as V4 errors on exactly those fields. The convenience max bound on score inputs updates immediately; stored values do not.
- **Widget bounds are convenience only:** `scale_max` number input (min 2, max 100, step 1); weights (min 0.0, max 1.0, step 0.01); scores (min 1, step 1). The gate is re-validated on Calculate regardless (e.g. typed "7.5" for a score is legal; a stale 12 after lowering the scale to 10 is caught).
- **Rounding discipline (A6):** the UI stores and submits full-precision floats from the widgets; it displays them only through `services.format_for_display` (the single 4-dp location). A displayed "0.3333" is never written back into the raw. Weight fields in the builder display the *typed* value (4-dp format string, same helper) — display only.

### 4.1 Implementation notes (2026-08-26 — flagged deviations, regression-pinned)

- **Score-input upper bound: `SCALE_MAX` (100), not the current scale (flagged deviation, framework-forced).** Streamlit 1.62's `number_input` **silently clamps** a stored session value that falls outside the widget's bounds — empirical: scale 10 with `p0_fap = 8`, then lowering the scale to 3 rewrote the stored value to 1. That is a silent modification of user data, which the rule above forbids. The implementation therefore sets the score inputs' `max_value` to the absolute ceiling `SCALE_MAX` (a constant, not a calculation) so no stored score can ever fall out of bounds; the validation gate remains the authority, and an orphaned score surfaces on Calculate as a V4 error on exactly that field (flow E3, pinned by `tests/test_ui_app.py` — including an assertion that the stored value was *not* clamped).
- **`st.rerun()` pattern:** state stored during a button click (Calculate result/rejection; two-click Reset arm and confirm) would otherwise only render on the next interaction, because the affected panels appear above the button in script order. `_run_calculation()` and the reset arm/confirm branches end with `st.rerun()` (same pattern as Add/Remove) so the outcome of the click the user just made is what the user sees.
- **Self-hosted fonts via data URIs:** Streamlit does not serve arbitrary files from the script directory, so `@font-face` rules are emitted only for `ui/fonts/lora-*.woff2` files that exist, base64-embedded in the single `<style>` block (still single-origin, no CDNs). The sandbox egress proxy blocked all font CDNs during implementation, so the assets are absent; the documented fallback stack applies (D-UI-1) and the rules activate automatically if the four documented files are added to `ui/fonts/` (see `ui/fonts/README.txt`).
- **Deprecated API avoided:** Streamlit 1.62 deprecates `use_container_width` (removal announced 2025-12-31); the implementation uses `width="stretch"` (verified warning-free under `-W error::DeprecationWarning`).

## 5. Error path → component mapping (normative)

`ValidationRejection.field` (contract in `validation-and-security.md`) maps to UI targets as follows. Translation to human labels is a **pure presentation mapping** (no math). The message shown is always the gate's `message` verbatim, prefixed by the translated label where the field is specific.

| `field` value | UI target | Human label |
|---|---|---|
| `product` | product input (Part I) | "Product name" |
| `scale_max` | scale input (Part I) | "Scale maximum" |
| `parameters` | Part II header (list-level) | "Parameters" |
| `parameters[{i}]` | card {i+1} header | "Parameter {i+1}" |
| `parameters[{i}].name` | name field of card {i+1} | "Name of parameter {i+1}" |
| `parameters[{i}].weight` | weight field of card {i+1} | "Weight of parameter {i+1}" |
| `parameters[{i}].scores` | scores block of card {i+1} | "Scores of parameter {i+1}" |
| `parameters[{i}].scores.{fap\|sap\|dap}` | that group's score field | "{Fully\|Specially\|Differently} Abled People (FAP/SAP/DAP) score of parameter {i+1}" |
| `group_weights` | summary panel only (unreachable from raw input — defensive) | "Internal group weights" |
| `""` (V-UNEXPECTED) | summary panel only, generic message | "Something went wrong. Please try again." (verbatim) |

Rules: exactly one rejection is shown per Calculate (fail-fast, first rule — the gate's contract); the previous field errors clear when a new Calculate is pressed; if the referenced parameter index no longer exists (user deleted the card since the error), the error renders in the summary panel only (graceful degradation — flagged behavior, not a defect).

`ServiceError` (fixed generic message) and V-UNEXPECTED render identically: summary panel, no field highlight, message verbatim ("Something went wrong. Please try again."). The diagnostics boundary (redaction) lives in the Application/Diagnostics layers, not the UI.

## 6. The Application-layer surface the UI requires

The UI task **depends on the services task landing first**. Required contract (recorded here so the services task is unambiguous; additive items are flagged):

| Item | Contract | Status |
|---|---|---|
| `services.evaluate(raw) -> EvaluationOutcome` | Wraps `validate(raw)` → `compute(evaluation)` → `EvaluationOutcome`; raises `ValidationRejection` (field/field-path intact) or `ServiceError` (fixed generic message; unexpected exceptions caught at this boundary, logged via diagnostics with redaction) | Planned (next task) |
| `services.format_for_display(value: float) -> str` | The single A6 rounding location: 4 decimal places, fixed-point string (`"0.6230"`), no clamping (a C1-tolerated value > 1 prints as-is, e.g. `"1.0000"`-style faithful output) | Planned (next task) |
| Live weight-total indicator | Would require a presentation helper (e.g. `services.weight_status(weights) -> str`) | **Not in baseline (D-UI-7):** the baseline shows the static hint "Weights must sum to 1.00" and surfaces sum errors after Calculate. Adding the live indicator later is an additive change-control item |

## 7. Safety rules (normative)

1. **No unescaped user strings in rich contexts.** Product names and parameter names may legally contain markdown/HTML-significant characters (`*`, `[`, `]`, `<`, backticks — none are control characters, so V18 does not block them). Therefore: every user string rendered in an HTML context is passed through `html.escape()`; baseline rendering paths (`st.text`, `st.dataframe`) are chosen for their default escaping; the HTML-table alternative is permitted only with the escape rule enforced by a unit test.
2. No `eval`/`exec`/dynamic imports/`shell`/unsafe deserialization anywhere in `ui/` (forbidden-construct policy extends to the UI band; AST scan in the future security audit).
3. No network calls from the UI other than the app server's own static-asset requests (fonts). No third-party CDNs.
4. `unsafe_allow_html=True` is used **only** for the static `<style>` block and (if chosen) the escaped results table — never with interpolated unescaped user data.
5. Session state is per-session (Streamlit default); nothing is written to disk (M8); no cookies, no analytics.

## 8. Parameter card layout (normative grid)

```
┌ Parameter 3                                            × ┐  ← header: Lora 600 15px + tertiary icon (44×44)
│ Name                                                    │
│ ┌────────────────────────────────────────────────────┐  │
│ │ e.g., Ease of reaching the handle                  │  │  ← text input
│ └────────────────────────────────────────────────────┘  │
│ Weight (sum of all weights must be 1.00)                │
│ ┌──────────────┐  ┌────────┐ ┌────────┐ ┌────────┐     │
│ │ 0.1667       │  │FAP  5  │ │SAP  4  │ │DAP  3  │     │  ← weight (w: 160px)
│ └──────────────┘  └────────┘ └────────┘ └────────┘     │     + 3 score inputs (equal width)
│     FAP — Fully Abled People   (group legend, caption,  │
│      first card only — repeated labels would be noise)  │
└─────────────────────────────────────────────────────────┘
```

Score inputs carry group abbreviation in the label (FAP/SAP/DAP); the full expansion appears once per card in caption text (first card: all three; subsequent cards: omitted — the legend is constant; flagged D-UI-8 for screen-reader consistency: the label is always the full "FAP score" string internally for accessibility — see `ACCESSIBILITY.md`).

Responsive: ≥720px as drawn; 480–720px: weight full-width row, scores 3-up; <480px: everything full-width (scores stack). The card never scrolls internally.

## 9. Results rendering (normative structure)

```
PART III — Results                                 [appears after first success]
┌─ (2px brand rule on top) ────────────────────────────────────────────┐
│ Accessible chair                     Scale 1–10 · 6 parameters ·    │
│ (Baskerville 24, from product field) Simple Mode (W = 0.3333 each)  │
│                                                                      │
│ ┌ Overall index ──────────────┐  ┌ FAP ─┐ ┌ SAP ┐ ┌ DAP ┐ ┌ Gap ─┐ │
│ │ UNIVERSALITY INDEX (UI)     │  │ 0.8200│ │0.5900│ │0.2500│ │0.5700│ │
│ │ 0.5533                      │  │Fully  │ │Spec. │ │Diff. │ │FAP  │ │
│ │ (range 0.0000–1.0000)       │  │Abled  │ │Abled │ │Abled │ │−DAP │ │
│ └─────────────────────────────┘  └───────┘ └─────┘ └─────┘ └──────┘ │
│                                                                      │
│ Per-parameter normalized scores (s ÷ scale)          [table]        │
│ Parameter   Weight   FAP      SAP      DAP                                │
│ Reachability  0.7000   1.0000   0.5000   0.1000                            │
│ Stability     0.3000   0.4000   0.8000   0.6000                            │
│ [optional second table: contributions w × s_norm — progressive          │
│  disclosure, collapsed by default]                                      │
│                                                                      │
│ Values shown to 4 decimal places; full-precision values were used in    │
│ all calculations. Computed locally — nothing was uploaded.             │
└──────────────────────────────────────────────────────────────────────┘
```

- All figures via `format_for_display`. The gap card's sub-label names the max/min groups ("FAP − DAP") — a pure ordering read of the three displayed values (no math: comparison of the three already-computed values to label them; flagged as the UI's second permitted non-display operation, a `max`/`min` for labeling only — D-UI-9).
- **Previous-results rule:** a failed Calculate keeps the previous results visible, dimmed to 60% opacity, with the caption "Showing previous calculation — new input was not accepted." A successful Calculate replaces them. Reset clears them.
- Empty state (no calculation yet): a dashed 1px `#C6CFDD` border block (r6) with centered Lora italic 14px "Results will appear here after calculation." — no illustration.

## 10. Test strategy for the UI band (recorded for the UI task)

- `ui/` is stdlib + Streamlit only (AST import policy extends the existing purity tests).
- `collect_raw` and the field-path → label mapping are pure functions → unit-tested without Streamlit.
- Rendering smoke tests via `streamlit.testing.v1.AppTest` (if available in the pinned version) for: happy path TV7 raw → results rendered with `format_for_display` strings; rejection path → error summary text verbatim; disabled states at n = 1 / n = 100; two-click reset.
- The forbidden-substring policy (no formula bodies, no `Σ`, no tolerance literals, no `1e-9`) applies to `ui/` as to `validation.py`.
- Escape-rule unit test: a product name containing `**bold**` and `<script>` renders inertly (no markdown/HTML execution).

## 11. Flagged design decisions (consolidated register)

| ID | Decision | Rationale / revert path |
|---|---|---|
| D-UI-1 | Baskerville = system stack (not embedded); Lora self-hosted | No licensed web font file exists for classic Baskerville. Change-control path: licensed OFL equivalent |
| D-UI-2 | No per-field success state (section-level success only) | Academic tone; green ticks read as gamification. Trivial to add later |
| D-UI-3 | Streamlit + CSS overrides; Option B (vanilla SPA) documented, unapproved | Contract says Streamlit; overrides are version-fragile → Option B is the explicit change-control escape hatch |
| D-UI-4 | Visible editable defaults: scale 5, weight 1.0, scores 1 | Number inputs cannot be blank; defaults are displayed, never hidden; gate remains authority |
| D-UI-5 | New parameter gets weight 0.0; no auto-redistribution | No automatic modification of entered data (mirrors the no-silent-fixing contract) |
| D-UI-6 | No parameter reordering | Entry order = deterministic summation order = display order |
| D-UI-7 | No live weight total in baseline (static hint + post-Calculate error) | A live total would require a new Application-layer helper (additive change control) |
| D-UI-8 | Group legend shown once per card set; internal labels always full | Calm visuals without sacrificing screen-reader clarity |
| D-UI-9 | Gap sub-label (max/min names) uses `max`/`min` on displayed values | Labeling only; the value itself is F4's output. The only two permitted UI operations besides formatting (§4, §9) |
