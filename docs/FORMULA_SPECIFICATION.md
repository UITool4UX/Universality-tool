# Formula specification — AUTHORITATIVE

This is the **single authoritative statement** of the formulas, constraints, numerical rules, and test vectors of this project. There is exactly one such statement in the repository; `computational-model.md` is now a redirect to this file. All code, tests, and UI must conform to it. Changes require the full change-control procedure (`changelog.md`, `../README.md`).

**Status: design contract — implemented.** The calculation engine
(`universality/calculation.py`) and the validation gate
(`universality/validation.py`) conform to this specification (both
implemented 2026-08-25; see `docs/changelog.md`).

**Provenance:** every formula below is **[P-BRIEF]** — specified by the project brief. The research pedigree of the exact formulas is **[P-UNVERIFIED]** until the full text of [S1] is cross-checked (`RESEARCH_BASIS.md`, U1). Nothing in this document claims 1:1 reproduction of the research methodology (A7).

## Notation

- `i` — index over the parameters of the evaluation, `i = 1…n`, with `1 ≤ n ≤ 100` (A11).
- `G` — index over the user groups: `F` = FAP, `S` = SAP, `D` = DAP (R2, R3).
- `scale_max` — maximum value of the satisfaction scale, **declared per evaluation by the student**: a positive integer, `2 ≤ scale_max ≤ 100` (A3). One scale applies to all parameters of that evaluation.
- `s(i, G)` — observed satisfaction score for parameter `i` and group `G`: a finite real in `[0, scale_max]` (C3). A single scalar per (parameter, group) pair (A17). **User-input gate:** `1 ≤ s ≤ scale_max` (A20, validation task 2026-08-25, explicit user instruction) — the formula/engine domain `[0, scale_max]` is unchanged.
- `w(i)` — weight of parameter `i`: a finite real in `[0, 1]` (C5).
- `W(G)` — weight of group `G`: a finite real in `[0, 1]` (C5).

## Formulas

**F1 — Normalization** (consistent with the primary formulation `UI = Σ(wᵢ × sᵢ) / max(S)`, [P-BRIEF]; within this project `max(S)` is the declared scale maximum — A16; the research meaning of `max(S)` remains U2):

    s_norm(i, G) = s(i, G) / scale_max

**F2 — Group indices:**

    UI_F = Σᵢ w(i) · s_norm(i, F)
    UI_S = Σᵢ w(i) · s_norm(i, S)
    UI_D = Σᵢ w(i) · s_norm(i, D)

**F3 — Overall index:**

    UI = W_F · UI_F + W_S · UI_S + W_D · UI_D

**F4 — user-group gap** (registered 2026-08-25, explicit user instruction; the interpretation is recorded as A19 in `ASSUMPTIONS.md`):

    group_gap = max(UI_F, UI_S, UI_D) − min(UI_F, UI_S, UI_D)

A derived diagnostic built solely from F2's outputs — no new normalization or weighting. Range: `[0, 1]` in exact arithmetic; `[0, 1 + EPSILON]` in floating point under the C1 tolerance.

F1–F4 are the **entire** calculation surface of the project (F1–F3 are [P-BRIEF]; F4 registered 2026-08-25). No other formula exists or may be added without change control.

## Constraints (must hold for every valid evaluation)

| # | Constraint | Check |
|---|---|---|
| C1 | Σᵢ w(i) = 1 | `abs(Σᵢ w(i) − 1.0) ≤ EPSILON` |
| C2 | W_F + W_S + W_D = 1 | `abs(Σ_G W(G) − 1.0) ≤ EPSILON` |
| C3 | 0 ≤ s_norm(i, G) ≤ 1 | guaranteed when `0 ≤ s(i, G) ≤ scale_max` |
| C4 | 0 ≤ UI ≤ 1 | follows from C1–C3 |
| C5 | w(i) ≥ 0 and W(G) ≥ 0 | negative weights are rejected (V5) |

`EPSILON = 1e−9` (application constant, A5). All floating-point equality checks use explicit tolerances; `==` is never used where a tolerance is appropriate.

## Simple Mode semantics (the only mode in the MVP)

- **Group weights:** W_F = W_S = W_D = 1/3. **Shown to the user.** Not editable in the MVP (A8). The application never derives or implies AHP weights (A1).
- **Parameter weights:** default `w(i) = 1/n`. **Shown to the user.** Editable by the student, who is responsible for any entered weights (e.g., from the student's own AHP analysis). The application validates C1/C5 only (A2).
- **Scale:** declared by the student per evaluation (A3), shown to the user.
- **Parameters:** named by the student (A10), `1 ≤ n ≤ 100` (A11).
- **Group coverage:** every parameter must have a score for **all three** groups (A15); a missing group score is an error (V14), never zero-filled.

## Numerical rules

1. **No rounding of intermediate calculations.** Compute in full IEEE-754 double precision.
2. **Round only when presenting results:** display to 4 decimal places (A6). Display rounding never feeds back into computation.
3. **Explicit floating-point tolerances** for equality checks (EPSILON above).
4. **Deterministic:** identical inputs produce identical results; no time, randomness, or global mutable state in the calculation.
5. Division by zero is impossible by construction: `scale_max ≥ 2` (V11) and `n ≥ 1` (V12).

## Canonical test vectors

The implementation **must** reproduce the exact rational values below, with a comparison tolerance of `1e−12` (never `==` on the overall results).

**TV1 — basic (scale 5, two parameters, weights 1/2 each):**
- `scale_max = 5`; `w(P1) = w(P2) = 1/2`; `W = (1/3, 1/3, 1/3)`
- `s(P1)`: FAP 5, SAP 4, DAP 3 → `s_norm`: `1, 4/5, 3/5`
- `s(P2)`: FAP 3, SAP 2, DAP 1 → `s_norm`: `3/5, 2/5, 1/5`
- Expected: `UI_F = 4/5 (0.8)`, `UI_S = 3/5 (0.6)`, `UI_D = 2/5 (0.4)`, **`UI = 3/5 (0.6)`**, `group_gap = 2/5 (0.4)`

**TV2 — boundary, all scores at maximum** (any `n`, any valid weights): every `s_norm = 1`, so `UI_F = UI_S = UI_D = 1` in exact arithmetic and **`UI = 1`** within floating-point rounding (compare with tolerance); `group_gap = 0` (all group indices equal).

**TV3 — boundary, all scores zero:** **`UI = 0` exactly** (bit-exact; zeros are exact in IEEE-754); `group_gap = 0` exactly. *(Engine-level vector: constructed directly on the domain. Since A20 (2026-08-25), score 0 is no longer producible from user input through the validation gate.)*

**TV4 — single parameter** (`n = 1`, `w = 1`): `UI_G = s_norm(P1, G)` and `UI = (UI_F + UI_S + UI_D)/3`. Example: `scale_max = 10`, score 7 for all groups → `UI = 7/10 (0.7)`; `group_gap = 0` exactly (all group indices equal, 7/10).

**TV5 — hand-verifiable reference case** (scale 10; unequal parameter weights 0.7/0.3; unequal group weights 0.5/0.3/0.2):
- `scale_max = 10`; `w(A) = 0.7`, `w(B) = 0.3`; `W = (0.5, 0.3, 0.2)`
- `s(A)`: FAP 10, SAP 5, DAP 0 → `s_norm`: `1, 1/2, 0`
- `s(B)`: FAP 4, SAP 8, DAP 6 → `s_norm`: `2/5, 4/5, 3/5`
- Hand computation (every value an exact terminating decimal — full worksheet: `tests/CALCULATION_TEST_VECTORS.md`):
  `UI_F = 0.7·1 + 0.3·0.4 = 0.82 (41/50)`; `UI_S = 0.7·0.5 + 0.3·0.8 = 0.59 (59/100)`; `UI_D = 0.7·0 + 0.3·0.6 = 0.18 (9/50)`; **`UI = 0.5·0.82 + 0.3·0.59 + 0.2·0.18 = 0.623 (623/1000)`**; `group_gap = 0.82 − 0.18 = 0.64 (16/25)`
- Expected: the values above, within `1e−12`.

**TV6 — no-clamping behavior** (valid input whose C1-tolerated weight sum exceeds 1):
- `scale_max = 5`; weights `(0.5 + 2.5e−10, 0.5, 2.5e−10)` — C1: sum = `1 + 5e−10 ≤ 1 + EPSILON`, so this is a **valid** evaluation; all scores `5` (every `s_norm = 1`).
- Expected: `UI_F = UI_S = UI_D = Σ w ≈ 1.00000000000000005 > 1.0` — the engine must compute faithfully (**no clamping** to 1.0); assert `> 1.0` and `≤ 1 + EPSILON`. `UI > 1.0` and `≤ 1 + 2·EPSILON` (documented C4 floating-point bound). `group_gap = 0.0` exactly.
- The invalid counterpart (sum `1 + 5e−8`) is rejected at construction (C1) — never clamped, never repaired.

**TV7 — pipeline reference case (registered 2026-08-26, QA audit):** the same hand-verifiable style as TV5, but **user-constructible** (every score ≥ 1, so it passes the A20 validation gate) and therefore exercised end-to-end through `validate` → `compute` (`tests/test_integration.py`). The product name is metadata only — it enters no formula.
- `scale_max = 10`; `w(Reachability) = 0.7`, `w(Stability) = 0.3`; `W = (1/3, 1/3, 1/3)` (Simple Mode)
- `s(Reachability)`: FAP 10, SAP 5, DAP 1 → `s_norm`: `1, 1/2, 1/10`
- `s(Stability)`: FAP 4, SAP 8, DAP 6 → `s_norm`: `2/5, 4/5, 3/5`
- Hand computation (every value an exact terminating decimal):
  `UI_F = 0.7·1 + 0.3·(2/5) = 0.7 + 0.12 = 0.82 (41/50)`;
  `UI_S = 0.7·(1/2) + 0.3·(4/5) = 0.35 + 0.24 = 0.59 (59/100)`;
  `UI_D = 0.7·(1/10) + 0.3·(3/5) = 0.07 + 0.18 = 0.25 (1/4)`;
  **`UI = (0.82 + 0.59 + 0.25)/3 = 1.66/3 = 83/150 = 0.553333…`**;
  `group_gap = 0.82 − 0.25 = 0.57 (57/100)`
- Expected: the values above, within `1e−12`. (Verified pipeline output:
  `UI_F = 0.82`, `UI_S = 0.59`, `UI_D = 0.25`, `UI = 0.5533333333333333`,
  `group_gap = 0.57`.)

Any change to a formula, constraint, or default ⇒ updated test vectors + regression tests + changelog entry + explicit approval.
