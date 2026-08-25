# Limitations — the negative contract

Purpose: state, in one place, **what the tool does not claim, does not do, and must not implement yet** — and register every **ambiguity** in the source material with its impact and resolution path. This document is part of the methodology contract: omitting an item from the MVP silently is a defect.

Rule of consequence: **ambiguities block claims, not code.** Every ambiguity below has a documented current handling, so the MVP contract stays executable. Nothing marked [P-UNVERIFIED] in `RESEARCH_BASIS.md` may be promoted to fact from this document either.

## 1. Claim prohibitions (always in force)

- **No full-reproduction claim.** The tool never states or implies that it reproduces the complete Singh & Tandon (2016) methodology (A7). The A7 statement must be visible to users.
- **No interpretation bands.** No "0.80 = excellent" / "0.60 = average" or any threshold-derived verdict, ever, unless and until documented research support exists (A12, M3).
- **No verified-language for unverified claims.** UI, docs, and code comments may not describe [P-UNVERIFIED] content as established by the research.

## 2. Behavior prohibitions (MVP)

- No silent repair, imputation, or zero-filling of invalid or missing research data (A14, V14, A15, A17).
- No shifting of scores (e.g., `(s − 1)/(max − 1)` for 1-based instruments) — that alters the formula (A4, M10).
- No AHP computation, no weight generation of any kind by the application (A1, A2, M1).
- No partial group coverage: all three group scores are required per parameter (A15, M6).
- No persistence, no storage of evaluations (A13, M8).
- No statistical procedures of any kind (M9).

## 3. Must-NOT-implement list (gated items)

Each item is **prohibited from implementation** until its gate is satisfied. Gates are deliberate: they prevent the project from silently absorbing unverified methodology.

| # | Item | Why not yet | Gate (what would unblock it) |
|---|---|---|---|
| M1 | **AHP engine** (pairwise-comparison matrix, priority vector, consistency index) | AHP's role in [S1] is [P-UNVERIFIED] (U4); the MVP is mandated to never perform AHP | Full-text verification that [S1] uses AHP as specified **and** explicit approval **and** contract update |
| M2 | **Kano classification** (classification logic; Kano categories used in scoring; Kano-based scoring). **Scope note (2026-08-25):** the inert domain vocabulary type `KanoCategory` is explicitly approved (user instruction) — it carries no behavior, is not attached to any other model, and is not referenced by F1–F4; the gate stands for all Kano *behavior* | No available source connects Kano to [S1]/[S2] (U8) | Published source establishing the connection, verified per the upgrade path, **and** explicit approval |
| M3 | **Interpretation bands / thresholds** on UI values | No empirical definitions verified in any source (A12) | Documented research support for specific bands **and** explicit approval |
| M4 | **Fixed research parameter list** (pre-encoded values from [S1]) | The parameter list is not available (U5); encoding a guessed list would be invention | Full text of [S1] with the parameter list, verified line-by-line |
| M5 | **Editable group weights / weighted mode** (a user-facing mode in which students enter W_F/W_S/W_D). **Scope note (2026-08-25, validation task):** the validation layer exposes `validate_group_weights` (V20/V21 + value rules) and defensively validates the fixed Simple Mode constant — this enforces the C2 rule at the application gate and opens **no** mode: group weights are still not user input, the raw schema has no group-weight field, and the UI exposes no editor. The gate stands for any *user-editable* group weights | Not defined by the brief for the MVP; would change F3's semantics as shipped | Explicit user decision + contract update (new mode definition, test vectors) |
| M6 | **Partial group coverage** (evaluating fewer than three groups) | MVP mandates all three groups with 1/3 weights (A15) | Explicit user decision + contract update (e.g., re-normalized group weights, new vectors) |
| M7 | **Within-group aggregation engine** (raw individual responses → group score by mean/median/…) | The research's aggregation method is [P-UNVERIFIED] (U3); inventing one is prohibited (A17) | Full-text verification of the method **and** explicit approval |
| M8 | **Persistence / database** | No storage requirement exists (A13) | Explicit user decision; if added: parameterized queries only, re-validation on load |
| M9 | **Statistical procedures** (significance, reliability, confidence, …) | Full text unavailable; nothing verified, nothing specified | Full-text verification of the procedure **and** explicit approval |
| M10 | **Scale shifting** (normalizing 1-based instruments by `(s−1)/(max−1)`) | Would alter the authoritative formula without approval (A4) | Explicit approval of a formula change (full change-control procedure) |

## 4. Ambiguities register

| # | Ambiguity | Why it is ambiguous | Current handling (documented) | Impact if resolved differently | Resolution path |
|---|---|---|---|---|---|
| U1 | Does the exact formula in [S1] equal the brief's F1–F3? | Full text unavailable | Brief is authoritative for the MVP ([P-BRIEF]); no reproduction claim (A7) | Formula change → full change control, new test vectors | Upgrade path in `RESEARCH_BASIS.md` |
| U2 | Research meaning of `max(S)` in the primary formulation (scale maximum vs maximum observed score) | Full text unavailable; both readings are mathematically plausible | MVP reading fixed by the brief itself: `max(S) := scale_max` (A16); research meaning stays [P-UNVERIFIED] | If [S1] means observed-maximum normalization, that is a *different* operation — gated addition (M-style), not a silent change | Full-text verification |
| U3 | How individual user responses are aggregated into a per-group score | No source available specifies it; the brief speaks of scores as inputs | MVP takes a single scalar per (parameter, group) — an already-aggregated finding (A17); aggregation engine prohibited (M7) | An aggregation engine becomes a new, approved component with its own vectors | Full-text verification + user decision |
| U4 | Does [S1] derive parameter weights via AHP? | The brief's phrase "AHP-derived weights" is a hint, not a source | Application never performs AHP (A1, A2); students may enter weights from their own analysis; M1 gate stands | An AHP support feature (M1) could be admitted after verification | Full-text verification |
| U5 | What are the research's parameters ("user values")? | Not available in any accessible source | MVP: student-defined parameters (A2); no fixed list encoded (M4) | A verified fixed list could ship as a preset — never replacing student-defined mode | Full-text verification |
| U6 | What satisfaction scale did the research use? | Not available in any accessible source | MVP: student-declared scale, one per evaluation (A3) | A verified default could be offered as a preset; the engine formula is unchanged | Full-text verification |
| U7 | Does the research define group weights W_F, W_S, W_D (and what values)? | Not established by any available source | MVP: fixed 1/3 each, displayed, not editable (A1, A8); editing gated (M5) | Verified research weights would define a new mode after approval | Full-text verification + user decision |
| U8 | Is Kano part of the Singh–Tandon methodology? | No available source connects them | Kano treated as general literature only (K1); no formula references it; M2 gate stands | If a connection is verified and approved, Kano enters as a Research Mode feature | Published source verification |

## 5. Status

As of 2026-08-25: **all** ambiguities U1–U8 are open (full text of [S1]/[S2] unavailable). **Zero** items M1–M10 are unblocked. This is the intended state of the contract: the MVP is fully specified *despite* the open research questions, precisely because every open question has a documented, non-inventing handling.
