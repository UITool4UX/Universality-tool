# UX flow — Universality Index Tool (UI band)

**Status: design contract — implemented 2026-08-26 (`ui/app.py` + `ui/ui_model.py`); this document remains binding. Flagged deviations are recorded in `UI_ARCHITECTURE.md` §4.1 and `docs/changelog.md` (2026-08-26).**
Companions: `DESIGN_SYSTEM.md`, `UI_ARCHITECTURE.md`, `ACCESSIBILITY.md`.

## 1. Goal and non-goals

**User goal (verbatim product direction):** "I already did my research. I just need to enter my findings."
The interface is therefore a **structured transcription sheet**: one page, top-to-bottom, one action (Calculate), results read off like a report. No wizard, no onboarding, no tour, no settings.

**Non-goals (v0.1 — each requires change control to add):**
- No persistence, history, or multiple evaluations (M8; V15 export lane is separate).
- No accounts, sharing, or printing features (print is possible via the browser; not designed for).
- No live/inline recalculation while typing — calculation happens on Calculate (keeps the UI math-free; the gate is re-validated on each click).
- No i18n in v0.1 (English, `lang="en"`).
- No parameter reordering (D-UI-6), no live weight total (D-UI-7).
- No mobile app; responsive web only.

## 2. Page map (single page, document flow)

```
┌ MASTHEAD ────────────────────────────────────────────────────────────┐
│ Universality Index Tool            [Reset evaluation] (secondary)    │
│ Enter your user-research findings to calculate the Universality      │
│ Index.                                    v0.1.0 · Simple Mode      │
├ PART I — EVALUATION SETUP (white card) ──────────────────────────────┤
│ Product name                     │  Scale maximum (1 … 100)         │
│ [ e.g., Accessible chair ]       │  [ 5 ]  whole number, 2–100      │
├ PART II — PARAMETERS (white card, blue header band) ─────────────────┤
│ Parameters        3 of 100          [Reset weights to 1/n] (tert.)   │
│  ┌ Parameter 1 × ┐  Name / Weight / FAP / SAP / DAP                 │
│  ┌ Parameter 2 × ┐  …                                                │
│  ┌ Parameter 3 × ┐  …                                                │
│  [ + Add parameter ] (tertiary, dashed, full width)                  │
│  [ Calculate ] (primary)                                             │
├ PART III — RESULTS (light-blue block; placeholder before success) ───┤
│  [see UI_ARCHITECTURE.md §9]                                         │
├ FOOTER ──────────────────────────────────────────────────────────────┤
│ Scores are taken as given (no shifting or rescaling). This tool is a │
│ simplified implementation of the Singh & Tandon framework, not a     │
│ full reproduction of the research methodology. Computed locally.     │
└──────────────────────────────────────────────────────────────────────┘
```

- **Navigation:** none beyond the page. The masthead wordmark is not a link (there is no other page). Orientation comes from the I/II/III numbering and the blue header band. A sticky anchor index is a documented *optional enhancement* (not in baseline) for long evaluations.
- **Reading order = visual order = keyboard order** (single column; results below the form).

## 3. Form state machine

States: `FRESH` → `EDITING` → `CALCULATING` → `SUCCESS` | `ERROR` → `EDITING` …

```
            enter anything            press Calculate
 FRESH ───────────────────► EDITING ──────────────────┐
   ▲                        │  ▲                      ▼
   │ reset (2-click)        │  │ fix fields      CALCULATING
   │                        │  │                   │        │
   └────────────────────────┘  ◄───────────────────┤        │
                       success replaces      rejection/     │
                       outcome; error        ServiceError   │
                       keeps previous                            │
                       outcome (dimmed)                        ▼
```

| Transition | Rules (normative) |
|---|---|
| any → `EDITING` | Any widget interaction. No validation runs (the gate runs only on Calculate — calm, no premature error text). |
| `EDITING` → `CALCULATING` | Calculate pressed: button disabled ("Calculating…"), quiet progress line, results area at 40% opacity. |
| `CALCULATING` → `SUCCESS` | `services.evaluate` returned an outcome. Error cleared. Results rendered (fade-in 200ms, scroll-into-view 300ms — instant under reduced motion). Focus moves to the results heading (programmatic, `tabindex="-1"`). |
| `CALCULATING` → `ERROR` | `ValidationRejection`: error summary panel (role="alert") at the top of the affected part + inline errors under the target fields; previous outcome stays visible, dimmed, with "Showing previous calculation — new input was not accepted." `ServiceError`/V-UNEXPECTED: summary panel only (generic verbatim message), no field highlights. |
| `ERROR` → `EDITING` | Any interaction clears only the field errors that the user is editing (the field's error disappears when that widget changes value — the summary panel persists until the next Calculate; flagged behavior B-1). |
| any → `FRESH` | Two-click Reset: first click arms (label "Confirm reset — clears all entered data?", 5s auto-disarm); second click clears all state incl. outcome and errors. |

## 4. Event table (action → effect → no-silent-modification check)

| User action | Effect | Data modified? |
|---|---|---|
| Edit any field | state → `EDITING`; that field's inline error (if any) clears | user's own value |
| Change scale maximum | score inputs' convenience max updates; **stored scores untouched** | user's own value |
| Add parameter (n < 100) | new card appended: weight **0.0**, scores default, empty name; counter "n+1 of 100" | new empty parameter (D-UI-5: existing weights untouched) |
| Add at n = 100 | button disabled + caption "Maximum 100 parameters" | none |
| Remove parameter (n > 1) | card removed; keys deleted; re-indexed | the removed parameter only |
| Remove at n = 1 | × disabled (mirrors V12) | none |
| Reset weights to 1/n | every weight ← `1.0 / n` (defaults, not a fix) | all weights (explicit user action, button visible) |
| Calculate (success) | outcome stored & rendered; error cleared | none (inputs preserved) |
| Calculate (rejection) | rejection stored & rendered; previous outcome dimmed | none |
| Reset (2-click) | all state → `FRESH` (incl. outcome, errors) | everything (explicit 2-click) |

## 5. Happy path (reference scenario)

1. Student opens the page: Part I has an empty product name and scale `5`; Part II has **Parameter 1** (weight `1.0000`, scores `1`, `1`, `1`); Part III shows the placeholder. (Visible defaults — D-UI-4.)
2. Types product "Accessible chair"; keeps scale 5 or changes it (e.g., 10 — caption: "the maximum value of the satisfaction scale you used").
3. Adds parameters ("+ Add parameter"), fills name, weight, FAP/SAP/DAP scores per parameter. Weights start at 0.0000 for new cards; student either enters weights summing to 1.00 or presses "Reset weights to 1/n".
4. Presses **Calculate** → "Calculating…" (≤ a few hundred ms) → Part III fills in: overall UI (hero, 4 dp), FAP/SAP/DAP indices, group gap (with "max − min" sub-label), per-parameter normalized-scores table, the A6 note. Page scrolls to Part III.
5. Iterates: edits a score, presses Calculate again → results update in place (same position, no re-scroll if already visible).

## 6. Error flows (with exact on-screen strings)

- **E1 — missing/blank product** (V16): summary: "Missing value: product name is required." under Part I; product field highlighted.
- **E2 — weight sum 0.96** (V6): summary: "Invalid weights: parameter weights must sum to 1. (parameters)" — *never* auto-normalized; Part II header highlighted; no field-level target (list-level error). The static hint "Weights must sum to 1.00" sits under the weight row.
- **E3 — scale change orphans scores** (V4): e.g. scale lowered 10 → 5 with a stored 7: "Out-of-range score: parameters[0].scores.fap must lie between 1 and the declared scale maximum." under that exact field, label "Fully Abled People (FAP) score of parameter 1".
- **E4 — duplicate names** (V8): "Duplicate parameter name: 'P1' is already used. (parameters[1].name)" under the second name field.
- **E5 — internal failure** (ServiceError / V-UNEXPECTED): "Something went wrong. Please try again." summary panel only; previous results dimmed; nothing else changes.
- Each error flow ends the same way: user fixes → Calculate → success replaces the dimmed results.

## 7. Copy table (normative visible strings)

| Location | String |
|---|---|
| Page title (tab) | "Universality Index Tool" |
| Wordmark | "Universality Index Tool" |
| Purpose line | "Enter your user-research findings to calculate the Universality Index." |
| Masthead tag | "v0.1.0 · Simple Mode" |
| Part I title | "Part I — Evaluation setup" |
| Product label / placeholder | "Product name" / "e.g., Accessible chair" |
| Scale label / caption | "Scale maximum" / "The maximum value of the satisfaction scale you used (whole number, 2–100)." |
| Part II title / counter | "Part II — Parameters" / "{n} of 100" |
| Weight caption | "Weight" / "All weights must sum to 1.00." |
| Score labels | "FAP score" "SAP score" "DAP score" (internal/aria); visible micro-labels "FAP" "SAP" "DAP" |
| Group legend (first card) | "FAP — Fully Abled People · SAP — Specially Abled People · DAP — Differently Abled People" |
| Add parameter | "+ Add parameter" · disabled caption: "Maximum 100 parameters" |
| Reset weights | "Reset weights to 1/n" |
| Remove | (icon) aria-label "Remove parameter {n}" |
| Calculate | "Calculate" → "Calculating…" |
| Reset evaluation | "Reset evaluation" → armed: "Confirm reset — clears all entered data?" |
| Results placeholder | "Results will appear here after calculation." |
| Results heading | "Part III — Results" (visually the product name is the lead; the heading is present for a11y) |
| Success caption | "✓ Calculated" |
| Stale-results caption | "Showing previous calculation — new input was not accepted." |
| Overall stat | label "UNIVERSALITY INDEX (UI)" · caption "(range 0.0000–1.0000)" |
| Group stat sub-labels | "Fully Abled People" / "Specially Abled People" / "Differently Abled People" |
| Gap stat | label "USER-GROUP GAP" · sub-label "{MAX} − {MIN}" (e.g. "FAP − DAP") |
| Group-weights note | "Simple Mode — group weights: 0.3333 each (1/3, shown, not editable)" |
| Table caption | "Per-parameter normalized scores (s ÷ scale)" · second table: "Contribution to each group index (weight × normalized score)" |
| A6 note | "Values shown to 4 decimal places; full-precision values were used in all calculations." |
| Footer A4 | "Scores are taken as given — no shifting, rescaling, or normalization of your data." |
| Footer A7 | "This tool is a simplified implementation of the Singh & Tandon user-values framework, not a full reproduction of the research methodology." |
| Footer local note | "Calculated locally in your browser session — nothing is uploaded or stored." |

## 8. Loading / success / empty states (summary — visual detail in DESIGN_SYSTEM §6)

- **Loading:** button disabled + "Calculating…"; 2px brand progress line under the button (indeterminate, slow); results at 40% opacity. No modal, no full-page spinner. (Synchronous compute is fast; the state exists for consistency and reliability perception.)
- **Success:** results fade in; 2px brand top rule; "✓ Calculated" caption; scroll-into-view; focus to results heading; no confetti, no count-up, no toast (the results themselves are the success).
- **Empty:** initial form (defaults above); results placeholder (dashed block, italic line). The parameter list can never be visually empty (n ≥ 1 enforced in UI and by V12).

## 9. Flagged behaviors

| ID | Behavior | Rationale |
|---|---|---|
| B-1 | Summary panel persists after fixing fields until next Calculate | Avoids flicker; the gate is the decider; cheap to change |
| B-2 | Delete without confirmation (× at n > 1) | Modal friction > small re-entry cost for v0.1; revisit on feedback |
| B-3 | Stale field index (card deleted since error) renders in summary only | Graceful degradation; never an exception |
| B-4 | No re-scroll on recalculation when results already in view | Calm; avoids yanking the viewport |
