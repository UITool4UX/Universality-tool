# Methodology contract — methodology map, MVP, Research Mode

Purpose: the audited **methodology map** — the definition, mathematical role, mode placement, optionality, and user-visibility of every audited concept — plus the formal definitions of **MVP** and **Research Mode**.

Provenance tags ([P-BRIEF] / [P-PUBLIC] / [P-UNVERIFIED]) follow `RESEARCH_BASIS.md`. Nothing marked [P-UNVERIFIED] may be presented as established fact anywhere in the project.

## 1. The two modes

### MVP (Simple Mode) — the current implementation contract

The MVP is **fully specified by this contract set** and contains exactly:

- student-declared satisfaction scale (A3), student-defined parameters (A2),
- a required product name (A21),
- fixed group weights 1/3 each (A1), parameter-weight default 1/n (A2),
- normalization and weighted sums, plus the user-group gap (`FORMULA_SPECIFICATION.md`, F1–F4),
- all three group scores required per parameter (A15; user-input minimum score 1 — A20),
- a single output UI ∈ [0,1], displayed to 4 decimal places (A6),
- the explicit non-reproduction statement (A7).

It contains **no** AHP, **no** Kano, **no** interpretation bands, **no** persistence, **no** statistical procedures. The full must-not list is `LIMITATIONS.md` (M1–M10).

### Research Mode — a governed extension lane, not a feature list

**Research Mode** is defined as a *process*, not as a set of features: a future mode that brings the tool closer to the complete research methodology. A feature may enter Research Mode **only** after:

1. full-text verification against [S1]/[S2] (claim upgraded in `RESEARCH_BASIS.md`),
2. contract update (these documents + `changelog.md` entry),
3. explicit approval,
4. implementation with test vectors.

**As of 2026-08-25, zero Research Mode features are approved or specified.** Any document, UI text, or code comment suggesting otherwise is a defect.

### Mode-boundary rule

Unverified research content never crosses into behavior: [P-UNVERIFIED] claims stay out of the MVP, and may enter Research Mode only through the four steps above.

## 2. Methodology map — audited concepts

| # | Concept | Definition (provenance) | Mathematical role | In MVP? | In Research Mode? | Optional? | Must be user-visible? |
|---|---|---|---|---|---|---|---|
| 1 | **FAP** (Fully Abled People) | User group of fully abled people; one of the three ability/needs groups (R2 [P-PUBLIC], R3 [P-PUBLIC]) | Group index `F`; input scores `s(i,F)` to F1–F2; weighted by `W_F` in F3; scores mandatory (A15) | **Yes** (mandatory group) | Yes (core of research, R2) | **No** | **Yes** (label, inputs, outputs) |
| 2 | **SAP** (Specially Abled People) | User group of specially abled people (R2, R3 [P-PUBLIC]) | Group index `S`; as row 1, with `W_S` | **Yes** (mandatory group) | Yes (core of research) | **No** | **Yes** |
| 3 | **DAP** (Differently Abled People) | User group of differently abled people (R2, R3 [P-PUBLIC]) | Group index `D`; as row 1, with `W_D` | **Yes** (mandatory group) | Yes (core of research) | **No** | **Yes** |
| 4 | **User values / product parameters** | Research: values associated with the individual needs of user groups (R4 [P-PUBLIC], abstract-level; **specific list [P-UNVERIFIED], U5**). MVP: a named parameter defined by the student (A2, confirmed) | Index `i = 1…n`, `1 ≤ n ≤ 100` (A11); each contributes `w(i)·s_norm(i,G)` to F2 | **Yes** (student-defined set) | Yes (research parameter list, only if verified) | **No** (n ≥ 1) | **Yes** (names, weights) |
| 5 | **Satisfaction scores** | MVP: observed score for (parameter `i`, group `G`) on the declared scale, `0 ≤ s ≤ scale_max` ([P-BRIEF] + A3, A17); **user-input minimum is 1** (A20, explicit user instruction 2026-08-25 — validation gate only). Research instrument and within-group aggregation: **[P-UNVERIFIED] (U3, U6)** | Input to F1; normalized to `[0,1]` | **Yes** | Yes (with a verified instrument) | **No** (A15: all three groups per parameter) | **Yes** (inputs) |
| 6 | **Parameter importance weights w(i)** | Relative importance of parameter `i` in the universality assessment. Research origin (e.g., AHP): **[P-UNVERIFIED] (U4)**. MVP: student-supplied or 1/n default ([P-BRIEF] + A2) | Multiplier in F2; subject to C1 (sum = 1) and C5 (≥ 0) | **Yes** | Yes (with verified derivation) | **No** (a default exists) | **Yes** (shown; editable, A2) |
| 7 | **User-group weights W(G)** | Relative weight of each user group in the overall index. Whether the research defines such weights: **[P-UNVERIFIED] (U7)**. MVP: fixed 1/3 each, not editable ([P-BRIEF] + A1, A8) | Multiplier in F3; subject to C2 | **Yes** (fixed) | Yes (only if verified) | **No** | **Yes** (display only) |
| 8 | **Normalization** | Mapping of an observed score to `[0,1]` by division by the declared scale maximum: F1. Research meaning of `max(S)` in the primary formulation: **[P-UNVERIFIED] (U2)**; the MVP interpretation is fixed by the brief (A16) | F1; makes C3 → C4 hold (UI ∈ [0,1]) | **Yes** | Yes | **No** | **Yes** (scale declaration; as-given scores note, A4) |
| 9 | **Universality Index** | Normalized overall measure of a product/service's universality across the three groups, `UI ∈ [0,1]`. Research: a model to assess universality exists (R1 [P-PUBLIC]); **its exact formula [P-UNVERIFIED] (U1)** | Output of F3 | **Yes** (the primary output) | Yes | **No** | **Yes** (4 decimal places, A6) |
| 10 | **Kano categories** | General Kano model: attribute classes by shape of satisfaction response (must-be, one-dimensional, attractive, indifferent, reverse) (K1 [P-PUBLIC], [M1]). **Connection to the Singh–Tandon methodology: [P-UNVERIFIED] (U8)** | **None in the current contract** — no formula references Kano | **No feature** (an inert domain vocabulary type `KanoCategory` was implemented 2026-08-25 per explicit user instruction — no behavior, no attachment, no formula reference; see M2 scope note) | Only if verified (gate M2) | Yes (pure extension, if ever admitted) | **No** (until verified and admitted) |
| 11 | **AHP weighting** | General method: pairwise comparison (1–9 scale) → priority vector with consistency check (K2 [P-PUBLIC], [M2]). **Use in [S1]: [P-UNVERIFIED] (U4)** — the brief's phrase "AHP-derived weights" is the only hint | **None in the current contract** — the MVP never performs AHP; weights are inputs | **No** (mandated: the app never performs or implies AHP — A1, A2) | Candidate weight-derivation support, only after full-text verification + approval (gate M1) | Yes (if ever admitted) | **No** (at most: a note that students may enter weights from their own AHP analysis — never derived by the app) |
| 12 | **MVP vs full-methodology distinction** | The three-layer claim discipline: research methodology / simplified computational implementation / application assumptions; no full-reproduction claim ([P-BRIEF], A7, mandated) | None (governance, not mathematics) | **Yes** — the distinction is part of the MVP's own contract | It is the lane's definition | **No** | **Yes** (A7 statement in the UI; `LIMITATIONS.md`) |
| 13 | **User-group gap** | Spread of the group indices: F4 (registered 2026-08-25, explicit user instruction; interpretation A19). Project-derived diagnostic — not a research claim | F4; built solely from F2 outputs; range [0,1] exact / [0,1+EPSILON] FP | **Yes** (MVP; computed in the engine, exposed in the result) | n/a (MVP diagnostic) | **No** (always computed) | **Yes** (result field) |

## 3. Audit disposition summary

- **Core to both modes (no ambiguity):** concepts 1–9 — all [P-PUBLIC] or [P-BRIEF], fully specified by `FORMULA_SPECIFICATION.md` and `ASSUMPTIONS.md`.
- **Not in the MVP, not yet in Research Mode (gated):** concepts 10–11 — Kano and AHP exist only as general literature [P-PUBLIC]; their methodological role is [P-UNVERIFIED]. They are listed in `LIMITATIONS.md` as M1/M2 must-not-implement items.
- **Governance concept:** concept 12 — mandated, visible, non-negotiable.
- **Project-derived diagnostic:** concept 13 (user-group gap) is a project-derived diagnostic registered 2026-08-25 (F4); it carries no research claim.
